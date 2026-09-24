// The camera. Everything else fades away: over the live picture only a faint
// outline of the notebook stays, its ruled lines and red margin, to line the
// working up with, and the capture button. What is inside the outline is what
// gets read, so there is no crop step; "Adjust" crops the same photo again when
// the math spilled outside. "Choose a photo" opens the gallery, and is the way
// in on a computer without a camera. Photos never leave the device and are
// forgotten when the camera closes.

import { t } from "./i18n.js";

const LONGEST = 2400; // a gallery photo is scaled down to this many pixels at most
const NUDGE = 0.01; // an arrow key moves a crop corner by 1% of the photo (5% with Shift)

export class Camera {
  constructor(dialog, { onPhoto }) {
    this.dialog = dialog;
    this.onPhoto = onPhoto;
    this.video = dialog.querySelector(".camera-video");
    this.still = dialog.querySelector(".camera-still");
    this.guide = dialog.querySelector(".camera-guide");
    this.status = dialog.querySelector(".camera-status");
    this.progress = dialog.querySelector(".camera-progress");
    this.cropBox = dialog.querySelector(".crop-box");
    this.stream = null;
    this.photo = null; // { canvas, crop } of the last photo, for Adjust
    this.crop = null;

    dialog.querySelector(".camera-shutter").addEventListener("click", () => this.capture());
    dialog.querySelector(".camera-close").addEventListener("click", () => this.close());
    dialog.querySelector(".crop-read").addEventListener("click", () => this.#readCrop());
    dialog.querySelector(".crop-cancel").addEventListener("click", () => this.close());
    const input = dialog.querySelector(".camera-file");
    input.addEventListener("change", () => {
      if (input.files[0]) this.#fromFile(input.files[0]);
      input.value = "";
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    this.#setUpCrop();
  }

  #mode(mode) {
    this.dialog.dataset.mode = mode;
  }

  async open() {
    this.setStatus("");
    this.showProgress(null);
    this.#mode("starting");
    if (!this.dialog.open) this.dialog.showModal();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      this.video.srcObject = this.stream;
      await this.video.play();
      this.#mode("live");
      this.dialog.querySelector(".camera-shutter").focus();
    } catch {
      this.#stop();
      this.#mode("no-camera");
      this.setStatus(t("camera.noCamera"));
      this.dialog.querySelector(".camera-choose").focus();
    }
  }

  // The frame, frozen; the part inside the outline is what is read.
  capture() {
    const { videoWidth: width, videoHeight: height } = this.video;
    if (!width || !height) return;
    this.still.width = width;
    this.still.height = height;
    this.still.getContext("2d").drawImage(this.video, 0, 0, width, height);
    const crop = this.#guideCrop(width, height);
    this.#stop();
    this.#deliver(crop);
  }

  // Where the outline is, in the photo's own pixels (the video fills the screen
  // like object-fit: cover, so part of it is off the screen).
  #guideCrop(width, height) {
    const view = this.video.getBoundingClientRect();
    const guide = this.guide.getBoundingClientRect();
    const scale = Math.max(view.width / width, view.height / height);
    const offsetX = (view.width - width * scale) / 2 + view.left;
    const offsetY = (view.height - height * scale) / 2 + view.top;
    const left = Math.max(0, (guide.left - offsetX) / scale);
    const top = Math.max(0, (guide.top - offsetY) / scale);
    const right = Math.min(width, (guide.right - offsetX) / scale);
    const bottom = Math.min(height, (guide.bottom - offsetY) / scale);
    return { x: left, y: top, width: right - left, height: bottom - top };
  }

  async #fromFile(file) {
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      const scale = Math.min(1, LONGEST / Math.max(bitmap.width, bitmap.height));
      this.still.width = Math.round(bitmap.width * scale);
      this.still.height = Math.round(bitmap.height * scale);
      this.still.getContext("2d").drawImage(bitmap, 0, 0, this.still.width, this.still.height);
      bitmap.close();
    } catch {
      this.setStatus(t("camera.badPhoto"));
      return;
    }
    this.#stop();
    // a photo from the gallery was not lined up with the outline: show it whole
    // with a crop box, and read it when the student says so
    this.photo = { canvas: this.still, crop: { x: 0, y: 0, width: this.still.width, height: this.still.height } };
    this.adjust();
  }

  #deliver(crop) {
    this.photo = { canvas: this.still, crop };
    this.#mode("reading");
    this.onPhoto(this.photo);
  }

  // The frozen photo with a crop box around what is read; "Read" reads it again.
  adjust() {
    if (!this.photo) return;
    if (!this.dialog.open) this.dialog.showModal();
    this.setStatus("");
    this.showProgress(null);
    this.crop = { ...this.photo.crop };
    this.#mode("adjust");
    requestAnimationFrame(() => {
      this.#placeCrop();
      this.dialog.querySelector(".crop-read").focus();
    });
  }

  #readCrop() {
    this.#deliver({ ...this.crop });
  }

  // how the still is shown (object-fit: contain): its scale and offset on screen
  #stillBox() {
    const view = this.still.getBoundingClientRect();
    const scale = Math.min(view.width / this.still.width, view.height / this.still.height);
    return {
      scale,
      left: view.left + (view.width - this.still.width * scale) / 2,
      top: view.top + (view.height - this.still.height * scale) / 2,
    };
  }

  #placeCrop() {
    const { scale, left, top } = this.#stillBox();
    const dialogBox = this.dialog.getBoundingClientRect();
    Object.assign(this.cropBox.style, {
      left: `${left - dialogBox.left + this.crop.x * scale}px`,
      top: `${top - dialogBox.top + this.crop.y * scale}px`,
      width: `${this.crop.width * scale}px`,
      height: `${this.crop.height * scale}px`,
    });
  }

  // Corners move one edge pair each; the box itself moves whole.
  #setUpCrop() {
    const limits = () => ({ width: this.still.width, height: this.still.height });
    const apply = (part, dx, dy) => {
      const { width, height } = limits();
      const minimum = Math.min(width, height) * 0.05;
      let { x, y, width: w, height: h } = this.crop;
      let right = x + w;
      let bottom = y + h;
      if (part === "move") {
        x = Math.min(Math.max(0, x + dx), width - w);
        y = Math.min(Math.max(0, y + dy), height - h);
        right = x + w;
        bottom = y + h;
      } else {
        if (part.includes("left")) x = Math.min(Math.max(0, x + dx), right - minimum);
        if (part.includes("right")) right = Math.max(Math.min(width, right + dx), x + minimum);
        if (part.includes("top")) y = Math.min(Math.max(0, y + dy), bottom - minimum);
        if (part.includes("bottom")) bottom = Math.max(Math.min(height, bottom + dy), y + minimum);
      }
      this.crop = { x, y, width: right - x, height: bottom - y };
      this.#placeCrop();
    };
    let drag = null;
    this.cropBox.addEventListener("pointerdown", (event) => {
      const part = event.target.closest("[data-part]")?.dataset.part ?? "move";
      drag = { part, id: event.pointerId, x: event.clientX, y: event.clientY };
      this.cropBox.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    this.cropBox.addEventListener("pointermove", (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      const { scale } = this.#stillBox();
      apply(drag.part, (event.clientX - drag.x) / scale, (event.clientY - drag.y) / scale);
      drag.x = event.clientX;
      drag.y = event.clientY;
    });
    const end = (event) => {
      if (drag && event.pointerId === drag.id) drag = null;
    };
    this.cropBox.addEventListener("pointerup", end);
    this.cropBox.addEventListener("pointercancel", end);
    for (const handle of this.cropBox.querySelectorAll("[data-part]")) {
      handle.addEventListener("keydown", (event) => {
        const step = (event.shiftKey ? 5 : 1) * NUDGE;
        const { width, height } = limits();
        const moves = {
          ArrowLeft: [-step * width, 0],
          ArrowRight: [step * width, 0],
          ArrowUp: [0, -step * height],
          ArrowDown: [0, step * height],
        };
        if (!moves[event.key]) return;
        event.preventDefault();
        apply(handle.dataset.part, ...moves[event.key]);
      });
    }
    new ResizeObserver(() => this.dialog.dataset.mode === "adjust" && this.#placeCrop()).observe(this.dialog);
  }

  setStatus(text) {
    this.status.textContent = text;
  }

  // ``fraction`` from 0 to 1, or null to hide the bar
  showProgress(fraction) {
    this.progress.hidden = fraction === null;
    if (fraction !== null) this.progress.value = fraction;
  }

  #stop() {
    for (const track of this.stream?.getTracks() ?? []) track.stop();
    this.stream = null;
    this.video.srcObject = null;
  }

  // Fade away, back to the app; the photo is forgotten unless kept for Adjust.
  async close({ keepPhoto = false } = {}) {
    this.#stop();
    if (!keepPhoto) this.photo = null;
    if (!this.dialog.open) return;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      this.dialog.classList.add("leaving");
      await new Promise((resolve) => setTimeout(resolve, 260));
      this.dialog.classList.remove("leaving");
    }
    this.dialog.close();
  }
}
