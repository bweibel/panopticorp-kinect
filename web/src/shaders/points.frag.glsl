varying float vDepth;
varying float vValid;

// Panopticorp palette: deep black bg, phosphor green near, teal/cyan far
const vec3 COLOR_NEAR = vec3(0.08, 1.0, 0.35);   // hot phosphor green
const vec3 COLOR_FAR  = vec3(0.0,  0.55, 0.75);  // cool surveillance teal

void main() {
  // Discard padding slots (zero-position points that fill the buffer)
  if (vValid < 0.5) discard;

  // Circular point mask — gl_PointCoord is (0,0) top-left to (1,1) bottom-right
  vec2 uv = gl_PointCoord - 0.5;
  if (dot(uv, uv) > 0.25) discard;   // 0.25 = 0.5² — outside circle radius

  vec3 color = mix(COLOR_NEAR, COLOR_FAR, vDepth);

  // Soft edge fade toward circle boundary
  float edge = 1.0 - smoothstep(0.18, 0.25, dot(uv, uv));
  float alpha = edge * (1.0 - vDepth * 0.3);  // far points slightly more transparent

  gl_FragColor = vec4(color, alpha);
}
