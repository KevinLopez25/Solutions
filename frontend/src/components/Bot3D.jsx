export default function Bot3D({ onToggle, isActive = false }) {
  return (
    <>
      {/* Robot grande — lado izquierdo, detrás del contenido */}
      <div className="bot3d bot3d-full" aria-hidden="true">
        <div className="bwrap">
          <div className="body">
            <div className="head">
              <div className="antenna" />
              <div className="face">
                <div className="scan" />
                <div className="eyes">
                  <div className="eye" />
                  <div className="eye" />
                </div>
                <div className="mouth" />
              </div>
            </div>
            <div className="arm l" />
            <div className="arm r" />
            <div className="torso">
              <div className="core" />
              <div className="panel">
                <div className="dot" />
                <div className="dot" />
                <div className="dot" />
              </div>
              <div className="circuit-light a" />
              <div className="circuit-light b" />
              <div className="circuit-light c" />
            </div>
            <div className="leg l" />
            <div className="leg r" />
          </div>
          <div className="ring" />
          <div className="gadget gadget-a" />
          <div className="gadget gadget-b" />
          <div className="gadget gadget-c" />
        </div>
      </div>

      {/* Robot pequeño — esquina inferior derecha, abre el chat */}
      <div
        className={`bot3d bot3d-chat${isActive ? ' bot3d-chat-active' : ''}`}
        onClick={onToggle}
        role="button"
        aria-label="Abrir asistente"
        title="Asistente Periferia"
      >
        <div className="bwrap">
          <div className="orb" />
          <div className="propeller" />
          <div className="face">
            <div className="scan" />
            <div className="eyes">
              <div className="eye" />
              <div className="eye" />
            </div>
            <div className="mouth" />
          </div>
          <div className="ring" />
          {isActive && <div className="bot-active-dot" />}
        </div>
      </div>
    </>
  )
}
