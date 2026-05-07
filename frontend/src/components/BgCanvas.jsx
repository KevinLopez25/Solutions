import { useEffect, useRef } from 'react'

export default function BgCanvas() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    const orbs = [
      { x:.15, y:.18, r:.42, vx:.00018,  vy:.00012,  color:'rgba(0,210,100,',  alpha:.32 },
      { x:.78, y:.72, r:.36, vx:-.00014, vy:.00016,  color:'rgba(0,180,80,',   alpha:.26 },
      { x:.55, y:.38, r:.28, vx:.0002,   vy:-.0001,  color:'rgba(0,230,118,',  alpha:.22 },
      { x:.25, y:.82, r:.22, vx:-.0001,  vy:-.00018, color:'rgba(0,160,60,',   alpha:.18 },
      { x:.88, y:.22, r:.3,  vx:.00012,  vy:.00022,  color:'rgba(10,200,90,',  alpha:.24 },
    ]

    const particles = Array.from({ length: 60 }, () => ({
      x:  Math.random(),
      y:  Math.random(),
      vx: (Math.random() - .5) * .00025,
      vy: (Math.random() - .5) * .00025,
      alpha: Math.random() * .4 + .1,
      r:  Math.random() * 1.8 + .6,
    }))

    let t = 0
    let raf

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }

    function draw() {
      const W = canvas.width
      const H = canvas.height
      t += 1

      const bg = ctx.createLinearGradient(0, 0, 0, H)
      bg.addColorStop(0, '#040906')
      bg.addColorStop(1, '#050D07')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, W, H)

      for (const o of orbs) {
        o.x += o.vx; o.y += o.vy
        if (o.x < -o.r) o.x = 1 + o.r
        if (o.x > 1 + o.r) o.x = -o.r
        if (o.y < -o.r) o.y = 1 + o.r
        if (o.y > 1 + o.r) o.y = -o.r

        const pulse = 1 + Math.sin(t * .012) * .04
        const rx = o.x * W, ry = o.y * H
        const rr = o.r * Math.min(W, H) * pulse

        const grad = ctx.createRadialGradient(rx, ry, 0, rx, ry, rr)
        grad.addColorStop(0,  o.color + o.alpha + ')')
        grad.addColorStop(.5, o.color + (o.alpha * .4) + ')')
        grad.addColorStop(1,  o.color + '0)')
        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.arc(rx, ry, rr, 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.strokeStyle = 'rgba(0,200,80,0.032)'
      ctx.lineWidth = 1
      const step = 80
      for (let x = 0; x < W; x += step) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke()
      }
      for (let y = 0; y < H; y += step) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke()
      }

      for (const p of particles) {
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = 1; if (p.x > 1) p.x = 0
        if (p.y < 0) p.y = 1; if (p.y > 1) p.y = 0
        const flicker = p.alpha * (.8 + Math.sin(t * .05 + p.r * 100) * .2)
        ctx.globalAlpha = flicker
        ctx.fillStyle = '#00E676'
        ctx.beginPath()
        ctx.arc(p.x * W, p.y * H, p.r, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1

      raf = requestAnimationFrame(draw)
    }

    resize()
    window.addEventListener('resize', resize)
    draw()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed', inset: 0, zIndex: 0,
        width: '100%', height: '100%', pointerEvents: 'none',
      }}
    />
  )
}
