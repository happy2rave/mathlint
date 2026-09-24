// The recognizer, read from recognizer.bin and run layer by layer.
//
// training/export.py writes the file: "MLREC001", the header's length, a JSON
// header (settings, vocabulary, where each tensor is), then the tensors — int8
// with a scale per row, or float32. They are turned back into float32 once,
// here. The layers are built from the settings exactly as training/mathrec/
// model.py builds them, so the two read an image the same way.

import {
  addInto,
  attend,
  conv2d,
  layerNorm,
  linear,
  relu,
  sinusoid,
} from "./layers.js";

const MAGIC = "MLREC001";

export function parseModel(buffer) {
  const bytes = new Uint8Array(buffer);
  const magic = String.fromCharCode(...bytes.subarray(0, 8));
  if (magic !== MAGIC) throw new Error("not a recognizer model");
  const length = new DataView(buffer).getUint32(8, true);
  const header = JSON.parse(new TextDecoder().decode(bytes.subarray(12, 12 + length)));
  const start = 12 + length;
  const tensors = {};
  for (const [name, entry] of Object.entries(header.tensors)) {
    const count = entry.shape.reduce((a, b) => a * b, 1);
    if (entry.dtype === "int8") {
      const quantized = new Int8Array(buffer, start + entry.offset, count);
      const rows = entry.shape[0];
      const scales = new Float32Array(buffer.slice(start + entry.scales, start + entry.scales + rows * 4));
      const perRow = count / rows;
      const values = new Float32Array(count);
      for (let i = 0; i < count; i++) values[i] = quantized[i] * scales[Math.floor(i / perRow)];
      tensors[name] = values;
    } else {
      tensors[name] = new Float32Array(buffer.slice(start + entry.offset, start + entry.offset + count * 4));
    }
  }
  return new Recognizer(header, tensors);
}

export class Recognizer {
  constructor(header, tensors) {
    this.config = header.config;
    this.tokens = header.tokens;
    this.special = header.special;
    this.height = header.height;
    this.stride = header.stride;
    this.t = tensors;
    this.cnn = this.#layout();
  }

  // The convolutional layers, named as in PyTorch's state dict.
  #layout() {
    const { channels, blocks } = this.config;
    const layers = [{ name: "cnn.0", cin: 1, out: channels[0], kernel: 3, stride: 2, groups: 1 }];
    let index = 2; // cnn.1 is the ReLU after the stem
    blocks.forEach((count, stage) => {
      for (let b = 0; b < count; b++) {
        const cin = b === 0 ? channels[stage] : channels[stage + 1];
        const cout = channels[stage + 1];
        const stride = b === 0 ? 2 : 1;
        layers.push({ name: `cnn.${index}`, separable: true, cin, cout, stride, shortcut: stride === 1 && cin === cout });
        index++;
      }
    });
    return layers;
  }

  // A prepared image (Uint8Array, 96 rows, ink dark) → the memory the decoder
  // reads: { values: cells × width, cells }.
  encode(pixels, width) {
    const stride = this.stride;
    const padded = Math.ceil(width / stride) * stride;
    let map = new Float32Array(this.height * padded); // ink 1, paper 0
    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < width; x++) map[y * padded + x] = 1 - pixels[y * width + x] / 255;
    }
    let shape = [1, this.height, padded];
    for (const layer of this.cnn) {
      if (!layer.separable) {
        [map, shape] = conv2d(map, shape, this.t[`${layer.name}.weight`], this.t[`${layer.name}.bias`], {
          out: layer.out, kernel: layer.kernel, stride: layer.stride, groups: 1,
        });
        relu(map);
        continue;
      }
      const input = map;
      let [inner, innerShape] = conv2d(map, shape, this.t[`${layer.name}.depthwise.weight`], this.t[`${layer.name}.depthwise.bias`], {
        out: layer.cin, kernel: 3, stride: layer.stride, groups: layer.cin,
      });
      relu(inner);
      [map, shape] = conv2d(inner, innerShape, this.t[`${layer.name}.pointwise.weight`], this.t[`${layer.name}.pointwise.bias`], {
        out: layer.cout, kernel: 1, stride: 1, groups: 1,
      });
      if (layer.shortcut) addInto(map, input);
      relu(map);
    }
    const [channels, rows, columns] = shape;
    const cells = rows * columns;
    const flat = new Float32Array(cells * channels); // cells × channels
    for (let c = 0; c < channels; c++) {
      for (let p = 0; p < cells; p++) flat[p * channels + c] = map[c * cells + p];
    }
    const d = this.config.width;
    let memory = linear(flat, cells, this.t["project.weight"], this.t["project.bias"], d);
    for (let r = 0; r < rows; r++) {
      const y = sinusoid(r, d / 2);
      for (let c = 0; c < columns; c++) {
        const x = sinusoid(c, d / 2);
        const at = (r * columns + c) * d;
        for (let i = 0; i < d / 2; i++) {
          memory[at + i] += y[i];
          memory[at + d / 2 + i] += x[i];
        }
      }
    }
    for (let l = 0; l < this.config.encoder_layers; l++) {
      const p = `encoder.${l}`;
      const normed = layerNorm(memory, d, this.t[`${p}.norm1.weight`], this.t[`${p}.norm1.bias`]);
      addInto(memory, this.#attention(`${p}.attention`, normed, cells, normed, cells));
      addInto(memory, this.#ffn(`${p}.ffn`, layerNorm(memory, d, this.t[`${p}.norm2.weight`], this.t[`${p}.norm2.bias`]), cells));
    }
    memory = layerNorm(memory, d, this.t["encoder_norm.weight"], this.t["encoder_norm.bias"]);
    return { values: memory, cells };
  }

  #project(name, x, length) {
    const d = this.config.width;
    return linear(x, length, this.t[`${name}.weight`], this.t[`${name}.bias`], d);
  }

  #attention(name, x, length, context, contextLength) {
    const d = this.config.width;
    const q = this.#project(`${name}.query`, x, length);
    const k = this.#project(`${name}.key`, context, contextLength);
    const v = this.#project(`${name}.value`, context, contextLength);
    const mixed = attend(q, length, k, v, contextLength, d, this.config.heads);
    return this.#project(`${name}.out`, mixed, length);
  }

  #ffn(name, x, length) {
    const hidden = this.t[`${name}.0.bias`].length;
    const inner = relu(linear(x, length, this.t[`${name}.0.weight`], this.t[`${name}.0.bias`], hidden));
    return linear(inner, length, this.t[`${name}.2.weight`], this.t[`${name}.2.bias`], this.config.width);
  }

  // Ready to decode: each decoder layer's keys and values over the memory,
  // computed once for the whole reading.
  begin(memory) {
    const layers = [];
    for (let l = 0; l < this.config.decoder_layers; l++) {
      const p = `decoder.${l}.cross_attention`;
      layers.push({
        keys: this.#project(`${p}.key`, memory.values, memory.cells),
        values: this.#project(`${p}.value`, memory.values, memory.cells),
      });
    }
    return { memory, cross: layers };
  }

  // One step: the token at ``position`` → the logits for the next token.
  // ``past`` holds this reading's self-attention keys and values so far (one
  // list per layer) and gets this step's added; it is copied, not changed, so
  // readings that share a start can share it.
  step(context, past, token, position) {
    const d = this.config.width;
    const scale = Math.sqrt(d);
    const embedding = this.t["embed.weight"].subarray(token * d, (token + 1) * d);
    const code = sinusoid(position, d);
    let x = new Float32Array(d);
    for (let i = 0; i < d; i++) x[i] = embedding[i] * scale + code[i];
    const next = [];
    for (let l = 0; l < this.config.decoder_layers; l++) {
      const p = `decoder.${l}`;
      const normed = layerNorm(x, d, this.t[`${p}.norm1.weight`], this.t[`${p}.norm1.bias`]);
      const key = this.#project(`${p}.self_attention.key`, normed, 1);
      const value = this.#project(`${p}.self_attention.value`, normed, 1);
      const keys = past ? [...past[l].keys, key] : [key];
      const values = past ? [...past[l].values, value] : [value];
      next.push({ keys, values });
      const query = this.#project(`${p}.self_attention.query`, normed, 1);
      const mixed = attend(query, 1, concat(keys, d), concat(values, d), keys.length, d, this.config.heads);
      addInto(x, this.#project(`${p}.self_attention.out`, mixed, 1));
      const crossQuery = this.#project(`${p}.cross_attention.query`, layerNorm(x, d, this.t[`${p}.norm2.weight`], this.t[`${p}.norm2.bias`]), 1);
      const { keys: memoryKeys, values: memoryValues } = context.cross[l];
      const crossed = attend(crossQuery, 1, memoryKeys, memoryValues, context.memory.cells, d, this.config.heads);
      addInto(x, this.#project(`${p}.cross_attention.out`, crossed, 1));
      addInto(x, this.#ffn(`${p}.ffn`, layerNorm(x, d, this.t[`${p}.norm3.weight`], this.t[`${p}.norm3.bias`]), 1));
    }
    x = layerNorm(x, d, this.t["decoder_norm.weight"], this.t["decoder_norm.bias"]);
    const logits = linear(x, 1, this.t["classify.weight"], this.t["classify.bias"], this.tokens.length);
    return { logits, past: next };
  }
}

function concat(rows, width) {
  const out = new Float32Array(rows.length * width);
  rows.forEach((row, i) => out.set(row, i * width));
  return out;
}
