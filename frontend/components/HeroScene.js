import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function HeroScene() {
  const mountRef = useRef(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const W = mount.clientWidth
    const H = mount.clientHeight

    // ── Scene ──────────────────────────────────────────────────────────────
    const scene    = new THREE.Scene()
    const camera   = new THREE.PerspectiveCamera(55, W / H, 0.1, 100)
    camera.position.set(0, 0, 6)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    mount.appendChild(renderer.domElement)

    // ── Materials ──────────────────────────────────────────────────────────
    const matBlue  = new THREE.MeshBasicMaterial({ color: 0x2563eb, wireframe: true })
    const matCyan  = new THREE.MeshBasicMaterial({ color: 0x60a5fa, wireframe: true })
    const matFaint = new THREE.MeshBasicMaterial({ color: 0x3b82f6, wireframe: true, transparent: true, opacity: 0.35 })

    // ── Central torus knot ─────────────────────────────────────────────────
    const knot = new THREE.Mesh(
      new THREE.TorusKnotGeometry(1.6, 0.38, 160, 20),
      matBlue
    )
    knot.position.set(2.2, 0, -1)
    scene.add(knot)

    // ── Floating shapes ────────────────────────────────────────────────────
    const floaters = []
    const configs = [
      { geo: new THREE.IcosahedronGeometry(0.55, 1),  pos: [-3.5,  1.2, -0.5], mat: matCyan  },
      { geo: new THREE.OctahedronGeometry(0.6, 0),     pos: [ 3.8, -1.4, -1.0], mat: matCyan  },
      { geo: new THREE.IcosahedronGeometry(0.35, 1),   pos: [-2.8, -1.6,  0.5], mat: matFaint },
      { geo: new THREE.TorusGeometry(0.5, 0.15, 12, 40), pos: [-4.2,  0.2, -2.0], mat: matFaint },
      { geo: new THREE.OctahedronGeometry(0.4, 0),     pos: [ 1.0,  2.4, -1.5], mat: matCyan  },
      { geo: new THREE.IcosahedronGeometry(0.28, 0),   pos: [ 4.5,  1.8, -0.5], mat: matFaint },
      { geo: new THREE.TorusGeometry(0.35, 0.1, 8, 30), pos: [-1.2, -2.4, -1.0], mat: matFaint },
    ]
    configs.forEach(({ geo, pos, mat }) => {
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.set(...pos)
      mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0)
      scene.add(mesh)
      floaters.push(mesh)
    })

    // ── Particle field ─────────────────────────────────────────────────────
    const N    = 1800
    const pos  = new Float32Array(N * 3)
    for (let i = 0; i < N * 3; i++) pos[i] = (Math.random() - 0.5) * 22
    const ptGeo = new THREE.BufferGeometry()
    ptGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const particles = new THREE.Points(ptGeo, new THREE.PointsMaterial({ color: 0x3b82f6, size: 0.03, transparent: true, opacity: 0.6 }))
    scene.add(particles)

    // ── Animation ──────────────────────────────────────────────────────────
    let raf
    const clock = new THREE.Clock()

    const animate = () => {
      raf = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()

      knot.rotation.x = t * 0.18
      knot.rotation.y = t * 0.28

      floaters.forEach((m, i) => {
        m.rotation.x += 0.004 + i * 0.001
        m.rotation.y += 0.006 + i * 0.001
        m.position.y  = configs[i].pos[1] + Math.sin(t * 0.6 + i * 1.2) * 0.18
      })

      particles.rotation.y = t * 0.04
      renderer.render(scene, camera)
    }
    animate()

    // ── Resize ─────────────────────────────────────────────────────────────
    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
      renderer.dispose()
    }
  }, [])

  return (
    <div
      ref={mountRef}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
    />
  )
}
