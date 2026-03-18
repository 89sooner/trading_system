const SVG_NS = "http://www.w3.org/2000/svg";

function createSvg(width, height) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  return svg;
}

function scale(value, min, max, outMin, outMax) {
  if (max <= min) {
    return (outMin + outMax) / 2;
  }
  const ratio = (value - min) / (max - min);
  return outMin + ratio * (outMax - outMin);
}

function makePoints(curve, valueKey, width, height, padding) {
  const valid = curve
    .map((p) => ({ x: Date.parse(p.timestamp), y: Number(p[valueKey]) }))
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));

  if (valid.length === 0) {
    return [];
  }

  const xMin = Math.min(...valid.map((p) => p.x));
  const xMax = Math.max(...valid.map((p) => p.x));
  const yMin = Math.min(...valid.map((p) => p.y));
  const yMax = Math.max(...valid.map((p) => p.y));

  return valid.map((p) => {
    const sx = scale(p.x, xMin, xMax, padding, width - padding);
    const sy = scale(p.y, yMin, yMax, height - padding, padding);
    return `${sx},${sy}`;
  });
}

export function renderTimeSeriesChart(container, curve, valueKey, color) {
  container.innerHTML = "";
  const width = 900;
  const height = 260;
  const padding = 26;

  const svg = createSvg(width, height);
  const points = makePoints(curve, valueKey, width, height, padding);

  if (points.length === 0) {
    container.textContent = "No chart data.";
    return;
  }

  const axis = document.createElementNS(SVG_NS, "line");
  axis.setAttribute("x1", String(padding));
  axis.setAttribute("y1", String(height - padding));
  axis.setAttribute("x2", String(width - padding));
  axis.setAttribute("y2", String(height - padding));
  axis.setAttribute("stroke", "#94a3b8");
  axis.setAttribute("stroke-width", "1");

  const polyline = document.createElementNS(SVG_NS, "polyline");
  polyline.setAttribute("points", points.join(" "));
  polyline.setAttribute("fill", "none");
  polyline.setAttribute("stroke", color);
  polyline.setAttribute("stroke-width", "2");

  svg.append(axis, polyline);
  container.append(svg);
}
