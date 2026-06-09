interface DepthOptionProps {
  selected: boolean
  onSelect: () => void
  sub: string
  title: string
  body: string
  link?: string
}

export function DepthOption({ selected, onSelect, sub, title, body, link }: DepthOptionProps) {
  return (
    <div
      className={'opt-card ' + (selected ? 'selected' : '')}
      onClick={onSelect}
      role="radio"
      aria-checked={selected}
      tabIndex={0}
    >
      <div
        className="mono"
        style={{
          fontSize: 10.5,
          letterSpacing: '0.14em',
          color: 'var(--ember-deep)',
          marginBottom: 8,
        }}
      >
        {sub}
      </div>
      <div className="serif" style={{ fontSize: 17.5, marginBottom: 7 }}>
        {title}
      </div>
      <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.6, textWrap: 'pretty' }}>
        {body}
      </p>
      {link ? (
        <a
          className="span-link"
          style={{ fontSize: 11.5, display: 'inline-block', marginTop: 10 }}
          href="#docs"
          onClick={(e) => e.preventDefault()}
        >
          {link}
        </a>
      ) : null}
    </div>
  )
}
