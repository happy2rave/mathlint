// The handful of layers the recognizer is made of, on plain Float32Arrays.
//
// Images and feature maps are channels × height × width, row after row;
// sequences are length × width. Nothing here allocates more than its output.

// A convolution with any kernel, stride and grouping, padded by kernel / 2
// with zeros, as PyTorch's Conv2d(padding=kernel // 2).
export function conv2d(input, [channels, height, width], weight, bias, { out, kernel, stride, groups }) {
  const pad = Math.floor(kernel / 2);
  const outH = Math.floor((height + 2 * pad - kernel) / stride) + 1;
  const outW = Math.floor((width + 2 * pad - kernel) / stride) + 1;
  const result = new Float32Array(out * outH * outW);
  if (kernel === 1 && stride === 1 && groups === 1) {
    pointwise(input, channels, height * width, weight, bias, out, result);
    return [result, [out, outH, outW]];
  }
  const perGroupIn = channels / groups;
  const perGroupOut = out / groups;
  for (let o = 0; o < out; o++) {
    const group = Math.floor(o / perGroupOut);
    const base = bias ? bias[o] : 0;
    const plane = o * outH * outW;
    for (let y = 0; y < outH; y++) {
      for (let x = 0; x < outW; x++) {
        let sum = base;
        for (let c = 0; c < perGroupIn; c++) {
          const channel = group * perGroupIn + c;
          const w0 = (o * perGroupIn + c) * kernel * kernel;
          for (let ky = 0; ky < kernel; ky++) {
            const iy = y * stride + ky - pad;
            if (iy < 0 || iy >= height) continue;
            const row = (channel * height + iy) * width;
            for (let kx = 0; kx < kernel; kx++) {
              const ix = x * stride + kx - pad;
              if (ix < 0 || ix >= width) continue;
              sum += input[row + ix] * weight[w0 + ky * kernel + kx];
            }
          }
        }
        result[plane + y * outW + x] = sum;
      }
    }
  }
  return [result, [out, outH, outW]];
}

// A 1×1 convolution: every pixel's channels times a matrix.
function pointwise(input, channels, pixels, weight, bias, out, result) {
  for (let o = 0; o < out; o++) {
    const row = result.subarray(o * pixels, (o + 1) * pixels);
    row.fill(bias ? bias[o] : 0);
    for (let c = 0; c < channels; c++) {
      const w = weight[o * channels + c];
      if (w === 0) continue;
      const plane = c * pixels;
      for (let p = 0; p < pixels; p++) row[p] += w * input[plane + p];
    }
  }
}

export function relu(values) {
  for (let i = 0; i < values.length; i++) if (values[i] < 0) values[i] = 0;
  return values;
}

export function addInto(target, values) {
  for (let i = 0; i < target.length; i++) target[i] += values[i];
  return target;
}

// x (length × inputs) times weight (outputs × inputs), plus bias.
export function linear(x, length, weight, bias, outputs) {
  const inputs = x.length / length;
  const result = new Float32Array(length * outputs);
  const whole = inputs - (inputs % 4);
  for (let n = 0; n < length; n++) {
    const offset = n * inputs;
    for (let o = 0; o < outputs; o++) {
      const w = o * inputs;
      // four running sums: the additions do not wait on each other
      let a = 0;
      let b = 0;
      let c = 0;
      let d = 0;
      let i = 0;
      for (; i < whole; i += 4) {
        a += x[offset + i] * weight[w + i];
        b += x[offset + i + 1] * weight[w + i + 1];
        c += x[offset + i + 2] * weight[w + i + 2];
        d += x[offset + i + 3] * weight[w + i + 3];
      }
      let sum = (bias ? bias[o] : 0) + (a + b) + (c + d);
      for (; i < inputs; i++) sum += x[offset + i] * weight[w + i];
      result[n * outputs + o] = sum;
    }
  }
  return result;
}

export function layerNorm(x, width, gamma, beta, eps = 1e-5) {
  const result = new Float32Array(x.length);
  for (let start = 0; start < x.length; start += width) {
    let mean = 0;
    for (let i = 0; i < width; i++) mean += x[start + i];
    mean /= width;
    let variance = 0;
    for (let i = 0; i < width; i++) variance += (x[start + i] - mean) ** 2;
    const scale = 1 / Math.sqrt(variance / width + eps);
    for (let i = 0; i < width; i++) {
      result[start + i] = (x[start + i] - mean) * scale * gamma[i] + beta[i];
    }
  }
  return result;
}

// Scaled dot-product attention, head by head: every query row looks at every
// key row (the decoder keeps only past keys, so no mask is needed here).
export function attend(q, queries, k, v, keys, width, heads) {
  const size = width / heads;
  const scale = 1 / Math.sqrt(size);
  const result = new Float32Array(queries * width);
  const scores = new Float64Array(keys);
  for (let h = 0; h < heads; h++) {
    const lane = h * size;
    for (let n = 0; n < queries; n++) {
      const query = n * width + lane;
      let best = -Infinity;
      for (let m = 0; m < keys; m++) {
        const key = m * width + lane;
        let dot = 0;
        for (let i = 0; i < size; i++) dot += q[query + i] * k[key + i];
        scores[m] = dot * scale;
        if (scores[m] > best) best = scores[m];
      }
      let total = 0;
      for (let m = 0; m < keys; m++) {
        scores[m] = Math.exp(scores[m] - best);
        total += scores[m];
      }
      for (let m = 0; m < keys; m++) {
        const weight = scores[m] / total;
        const value = m * width + lane;
        for (let i = 0; i < size; i++) result[query + i] += weight * v[value + i];
      }
    }
  }
  return result;
}

export function logSoftmax(values) {
  let best = -Infinity;
  for (const value of values) if (value > best) best = value;
  let total = 0;
  for (const value of values) total += Math.exp(value - best);
  const shift = best + Math.log(total);
  return Float64Array.from(values, (value) => value - shift);
}

// The Transformer's sine and cosine position code, as model.sinusoid.
export function sinusoid(position, width) {
  const code = new Float32Array(width);
  for (let i = 0; i < width / 2; i++) {
    const frequency = Math.exp(2 * i * (-Math.log(10000) / width));
    code[2 * i] = Math.sin(position * frequency);
    code[2 * i + 1] = Math.cos(position * frequency);
  }
  return code;
}
