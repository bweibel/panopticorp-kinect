uniform float uTime;
uniform float uPointSize;

varying float vDepth;   // 0 = near, 1 = far — used for color gradient in fragment
varying float vValid;   // 1 if this is a real point, 0 if padding (zero position)

void main() {
  vec4 worldPos = modelViewMatrix * vec4(position, 1.0);

  // Flag zero-position padding slots so fragment can discard them
  vValid = length(position) > 0.001 ? 1.0 : 0.0;

  // Normalized depth: sensor range is ~0.5-3.5m, mapped to 0-1
  // position.z is negative in Three.js camera space (we negated z on upload)
  float depthM = -worldPos.z;
  vDepth = clamp((depthM - 0.5) / 3.0, 0.0, 1.0);

  // Perspective-correct point size: closer points are larger
  // The sin pulse adds a subtle breathing animation
  float basePx = uPointSize * 1.5 / max(depthM, 0.1);
  gl_PointSize = basePx + sin(uTime * 1.8 + position.z * 0.004) * 0.4;

  gl_Position = projectionMatrix * worldPos;
}
