/*
  draws one highlight box per error on the current page, positioned by
  scaling each error's PDF-point bbox by displayScale (from PdfCanvas).
  no y-flip - see PdfCanvas.jsx's comment for why.
*/
export default function HighlightOverlay({ errors, displayScale, activeErrorIndex, onSelect }) {
  if (!displayScale) return null

  return (
    <div className="highlight-overlay">
      {errors.map((error, i) => {
        const [x0, y0, x1, y1] = error.bbox
        const isActive = i === activeErrorIndex

        return (
          <button
            key={i}
            type="button"
            className={`highlight-box${isActive ? ' highlight-box--active' : ''}`}
            style={{
              left: x0 * displayScale,
              top: y0 * displayScale,
              width: (x1 - x0) * displayScale,
              height: (y1 - y0) * displayScale,
              '--highlight-color': error.highlight_color,
            }}
            title={error.suggestion || error.text}
            onClick={() => onSelect?.(i)}
          />
        )
      })}
    </div>
  )
}
