import * as THREE from "three";
import { createCloud } from "./cloud";

const WS_URL = "ws://localhost:8765";
const RECONNECT_MS = 2000;

// ---- Scene setup ----

const glCanvas = document.getElementById("gl-canvas") as HTMLCanvasElement;
const renderer = new THREE.WebGLRenderer({ canvas: glCanvas, antialias: false });
renderer.setPixelRatio(window.devicePixelRatio);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);

// Camera sits at the sensor position looking into the room (+z world = -z Three.js)
const camera = new THREE.PerspectiveCamera(60, 1, 0.01, 20);
camera.position.set(0, 0, 0);
camera.lookAt(0, 0, -1);

const { points, uniforms, updateFromBuffer } = createCloud();
scene.add(points);

function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// ---- WebSocket ----

let pendingMeta: string | null = null;

function connect() {
  const ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => console.log("[ws] connected");

  ws.onmessage = (ev) => {
    if (typeof ev.data === "string") {
      pendingMeta = ev.data;
    } else {
      updateFromBuffer(ev.data as ArrayBuffer);
    }
  };

  ws.onclose = () => {
    console.log(`[ws] closed — reconnecting in ${RECONNECT_MS}ms`);
    setTimeout(connect, RECONNECT_MS);
  };

  ws.onerror = (e) => console.warn("[ws] error", e);
}

connect();

// ---- Render loop ----

const clock = new THREE.Clock();

function frame() {
  requestAnimationFrame(frame);
  uniforms.uTime.value = clock.getElapsedTime();
  renderer.render(scene, camera);
}

frame();
