"use client"

import { Canvas, useFrame, useLoader } from "@react-three/fiber"
import { TextureLoader } from "three"
import { Suspense, useEffect, useRef, useState } from "react"
import * as THREE from "three"

function canCreateRenderer() {
  if (typeof window === "undefined") return false
  try {
    const canvas = document.createElement("canvas")
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      alpha: true,
      powerPreference: "default",
      failIfMajorPerformanceCaveat: false,
      stencil: false,
    })
    renderer.dispose()
    return true
  } catch {
    return false
  }
}

function HeroFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center overflow-hidden bg-[#0A0A0A]">
      <div className="relative h-[520px] w-[520px]">
        <div
          className="absolute inset-0 overflow-hidden rounded-full border border-[#1D4ED8]/18"
          style={{
            backgroundImage: "url(https://unpkg.com/three-globe@2.30.0/example/img/earth-blue-marble.jpg)",
            backgroundSize: "220% 100%",
            backgroundRepeat: "repeat-x",
            backgroundPosition: "50% 50%",
            filter: "saturate(1.08) contrast(1.1)",
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.02), 0 0 42px rgba(59,130,246,0.08)",
            animation: "heroFloat 10s ease-in-out infinite",
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: "radial-gradient(circle at 30% 24%, rgba(255,255,255,0.46) 0%, rgba(255,255,255,0.18) 10%, rgba(255,255,255,0.06) 18%, transparent 32%)",
            mixBlendMode: "screen",
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: "radial-gradient(ellipse 78% 92% at 68% 52%, rgba(0,0,0,0) 34%, rgba(0,0,0,0.14) 52%, rgba(0,0,0,0.38) 70%, rgba(0,0,0,0.78) 100%)",
          }}
        />
        <div
          className="absolute inset-[-2.5%] rounded-full opacity-75"
          style={{
            background: "radial-gradient(circle at 50% 50%, transparent 64%, rgba(59,130,246,0.10) 78%, rgba(59,130,246,0.22) 88%, transparent 100%)",
          }}
        />
      </div>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.10),transparent_50%)]" />
      <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-[#0A0A0A] to-transparent pointer-events-none" />
    </div>
  )
}

function Globe() {
  const meshRef = useRef(null)
  const atmosphereRef = useRef(null)
  const texture = useLoader(TextureLoader, "https://unpkg.com/three-globe@2.30.0/example/img/earth-blue-marble.jpg")
  const [targetRotation, setTargetRotation] = useState({ x: 0.12, y: 0.15 })

  useFrame(() => {
    if (!meshRef.current || !atmosphereRef.current) return
    meshRef.current.rotation.y += 0.002
    meshRef.current.rotation.x += (targetRotation.x - meshRef.current.rotation.x) * 0.08
    meshRef.current.rotation.y += (targetRotation.y - meshRef.current.rotation.y) * 0.04
    atmosphereRef.current.rotation.x = meshRef.current.rotation.x
    atmosphereRef.current.rotation.y = meshRef.current.rotation.y
  })

  return (
    <group>
      <mesh
        ref={meshRef}
        onPointerMove={(event) => {
          const x = -(event.point.y / 2.5)
          const y = event.point.x / 2.5
          setTargetRotation({ x, y })
        }}
        onPointerOut={() => setTargetRotation({ x: 0.12, y: meshRef.current?.rotation.y ?? 0.15 })}
      >
        <sphereGeometry args={[2.15, 128, 128]} />
        <meshStandardMaterial map={texture} roughness={1} metalness={0} />
      </mesh>

      <mesh ref={atmosphereRef}>
        <sphereGeometry args={[2.24, 96, 96]} />
        <meshBasicMaterial color="#3B82F6" transparent opacity={0.08} side={THREE.BackSide} />
      </mesh>
    </group>
  )
}

function SceneCanvas() {
  return (
    <div className="absolute inset-0">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 1.25]}
        style={{ background: "transparent" }}
        gl={{ antialias: true, alpha: true, powerPreference: "default", failIfMajorPerformanceCaveat: false, stencil: false }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0)
        }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.7} />
          <directionalLight position={[5, 3, 5]} intensity={2.2} />
          <directionalLight position={[-3, -2, -5]} intensity={0.5} />
          <Globe />
        </Suspense>
      </Canvas>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.08),transparent_52%)] pointer-events-none" />
      <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-[#0A0A0A] to-transparent pointer-events-none" />
    </div>
  )
}

export default function EarthScene() {
  const [rendererReady, setRendererReady] = useState(null)

  useEffect(() => {
    setRendererReady(canCreateRenderer())
  }, [])

  if (rendererReady === null) {
    return <div className="absolute inset-0 bg-[#0A0A0A]" />
  }

  if (!rendererReady) {
    return <HeroFallback />
  }

  return <SceneCanvas />
}
