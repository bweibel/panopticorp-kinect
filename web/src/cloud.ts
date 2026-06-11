import * as THREE from "three";
import vertSrc from "./shaders/points.vert.glsl";
import fragSrc from "./shaders/points.frag.glsl";

const MAX_POINTS = 50_000;
const MM_TO_M = 0.001;

export interface CloudUniforms {
  uTime: THREE.IUniform<number>;
  uPointSize: THREE.IUniform<number>;
}

export function createCloud(): {
  points: THREE.Points;
  uniforms: CloudUniforms;
  updateFromBuffer: (buffer: ArrayBuffer) => number;
} {
  const positions = new Float32Array(MAX_POINTS * 3);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage)
  );
  // Draw only the populated slice each frame
  geometry.setDrawRange(0, 0);

  const uniforms: CloudUniforms = {
    uTime: { value: 0 },
    uPointSize: { value: 4.0 },
  };

  const material = new THREE.ShaderMaterial({
    vertexShader: vertSrc,
    fragmentShader: fragSrc,
    uniforms,
    transparent: true,
    depthWrite: false,
  });

  const points = new THREE.Points(geometry, material);

  function updateFromBuffer(buffer: ArrayBuffer): number {
    const view = new DataView(buffer);
    // header: uint32 frameId (LE) + uint16 numPoints (LE)
    const numPoints = Math.min(view.getUint16(4, true), MAX_POINTS);

    if (numPoints === 0) {
      geometry.setDrawRange(0, 0);
      return 0;
    }

    // Points are packed int16 x,y,z in mm — read as Int16Array directly (LE on x86)
    const src = new Int16Array(buffer, 6, numPoints * 3);
    const pos = geometry.attributes.position as THREE.BufferAttribute;
    const arr = pos.array as Float32Array;

    for (let i = 0; i < numPoints; i++) {
      const si = i * 3;
      arr[si]     =  src[si]     * MM_TO_M;  // x
      arr[si + 1] =  src[si + 1] * MM_TO_M;  // y (already y-up from Python)
      arr[si + 2] = -src[si + 2] * MM_TO_M;  // z: negate so cloud is in front of camera
    }

    pos.needsUpdate = true;
    geometry.setDrawRange(0, numPoints);
    return numPoints;
  }

  return { points, uniforms, updateFromBuffer };
}
