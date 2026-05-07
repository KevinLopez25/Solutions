export default function Bot3D() {
  return (
    <>
      {/* Robot grande — lado izquierdo, detrás del contenido */}
      <div className="bot3d bot3d-full" aria-hidden="true">
        <div className="bwrap">
          <div className="body">
            <div className="head">
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
            <div className="torso"><div className="core" /></div>
            <div className="leg l" />
            <div className="leg r" />
          </div>
          <div className="ring" />
        </div>
      </div>

      {/* Robot pequeño — esquina inferior derecha */}
      <div className="bot3d" aria-hidden="true">
        <div className="bwrap">
          <div className="orb" />
          <div className="face">
            <div className="scan" />
            <div className="eyes">
              <div className="eye" />
              <div className="eye" />
            </div>
            <div className="mouth" />
          </div>
          <div className="ring" />
        </div>
      </div>
    </>
  )
}
