"use client"

import { OrbitControls, useTexture } from "@react-three/drei"
import { Canvas, useFrame } from "@react-three/fiber"
import { Suspense, useMemo, useRef } from "react"
import * as THREE from "three"

function EarthBody() {
  const earthRef = useRef(null)
  const atmosphereRef = useRef(null)
  const texture = useTexture("https://unpkg.com/three-globe@2.30.0/example/img/earth-blue-marble.jpg")

  useFrame(() => {
    if (earthRef.current) earthRef.current.rotation.y += 0.0008
    if (atmosphereRef.current) atmosphereRef.current.rotation.y += 0.0008
  })

  return (
    <group rotation={[0, 0, 0.41]}>
      <mesh ref={earthRef}>
        <sphereGeometry args={[2, 64, 64]} />
        <meshPhongMaterial map={texture} />
      </mesh>
      <mesh ref={atmosphereRef}>
        <sphereGeometry args={[2.05, 64, 64]} />
        <meshPhongMaterial color="#3B82F6" transparent opacity={0.08} side={THREE.BackSide} />
      </mesh>
      <DataArcs />
      <NodeMarkers />
    </group>
  )
}

function Satellite({ orbitRadius, orbitSpeed, inclination }) {
  const ref = useRef(null)
  const angleRef = useRef(Math.random() * Math.PI * 2)

  const trail = useMemo(() => {
    const positions = []
    for (let i = 0; i <= 128; i += 1) {
      const angle = (i / 128) * Math.PI * 2
      positions.push(
        Math.cos(angle) * orbitRadius,
        Math.sin(angle) * inclination * orbitRadius,
        Math.sin(angle) * orbitRadius * Math.cos(inclination)
      )
    }
    return new Float32Array(positions)
  }, [inclination, orbitRadius])

  useFrame(() => {
    angleRef.current += orbitSpeed
    const angle = angleRef.current
    const x = Math.cos(angle) * orbitRadius
    const y = Math.sin(angle) * inclination * orbitRadius
    const z = Math.sin(angle) * orbitRadius * Math.cos(inclination)
    if (ref.current) {
      ref.current.position.set(x, y, z)
      ref.current.lookAt(0, 0, 0)
    }
  })

  return (
    <>
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" array={trail} count={trail.length / 3} itemSize={3} />
        </bufferGeometry>
        <lineBasicMaterial color="#1D4ED8" transparent opacity={0.15} />
      </line>
      <group ref={ref}>
        <mesh>
          <boxGeometry args={[0.04, 0.04, 0.12]} />
          <meshStandardMaterial color="#A3A3A3" />
        </mesh>
        <mesh position={[-0.1, 0, 0]}>
          <boxGeometry args={[0.12, 0.02, 0.04]} />
          <meshStandardMaterial color="#1D4ED8" />
        </mesh>
        <mesh position={[0.1, 0, 0]}>
          <boxGeometry args={[0.12, 0.02, 0.04]} />
          <meshStandardMaterial color="#1D4ED8" />
        </mesh>
      </group>
    </>
  )
}

function NodeMarkers() {
  const group = useRef(null)
  const nodes = useMemo(
    () => [
      { pos: [0.8, 1.8, 0.9], color: "#22C55E", offset: 0 },
      { pos: [-1.2, 1.6, 1.1], color: "#F59E0B", offset: 1 },
      { pos: [1.5, 1.2, -0.8], color: "#22C55E", offset: 2 },
      { pos: [-0.6, -1.7, 1.2], color: "#F59E0B", offset: 3 },
      { pos: [1.1, -1.5, -0.9], color: "#22C55E", offset: 4 },
      { pos: [-1.4, 1.0, 1.3], color: "#F59E0B", offset: 5 },
    ],
    []
  )

  useFrame(({ clock }) => {
    if (!group.current) return
    group.current.children.forEach((child, idx) => {
      const scale = 1 + Math.sin(clock.elapsedTime * 2 + nodes[idx].offset) * 0.25
      child.scale.setScalar(scale)
    })
  })

  return (
    <group ref={group}>
      {nodes.map((node, idx) => (
        <mesh key={idx} position={node.pos}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshStandardMaterial color={node.color} emissive={node.color} emissiveIntensity={0.8} />
        </mesh>
      ))}
    </group>
  )
}

function DataArcs() {
  const arcLines = useMemo(() => {
    const surface = [
      new THREE.Vector3(0.8, 1.8, 0.9),
      new THREE.Vector3(-1.2, 1.6, 1.1),
      new THREE.Vector3(1.5, 1.2, -0.8),
      new THREE.Vector3(-0.6, -1.7, 1.2),
      new THREE.Vector3(1.1, -1.5, -0.9),
      new THREE.Vector3(-1.4, 1.0, 1.3),
    ]
    const pairs = [
      [surface[0], surface[2]],
      [surface[1], surface[4]],
      [surface[3], surface[5]],
    ]
    return pairs.map(([a, b]) => {
      const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(2.8)
      const curve = new THREE.CatmullRomCurve3([a, mid, b])
      const points = curve.getPoints(40)
      return new Float32Array(points.flatMap((point) => [point.x, point.y, point.z]))
    })
  }, [])

  return (
    <group>
      {arcLines.map((positions, idx) => (
        <line key={idx}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" array={positions} count={positions.length / 3} itemSize={3} />
          </bufferGeometry>
          <lineBasicMaterial color="#3B82F6" transparent opacity={0.2} />
        </line>
      ))}
    </group>
  )
}

function ParticleField() {
  const ref = useRef(null)
  const particles = useMemo(() => {
    const positions = new Float32Array(500 * 3)
    for (let i = 0; i < 500; i += 1) {
      const radius = 8 + Math.random() * 4
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)
    }
    return positions
  }, [])

  useFrame(() => {
    if (ref.current) ref.current.rotation.y += 0.0001
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={particles} count={particles.length / 3} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.015} color="#1D4ED8" transparent opacity={0.3} />
    </points>
  )
}

export default function EarthScene() {
  return (
    <Canvas camera={{ fov: 45, position: [0, 0, 7] }} style={{ background: "transparent" }} gl={{ antialias: true, alpha: true }}>
      <Suspense fallback={null}>
        <EarthBody />
        <Satellite orbitRadius={3.2} orbitSpeed={0.004} inclination={0.3} />
        <Satellite orbitRadius={3.8} orbitSpeed={0.003} inclination={0.8} />
        <Satellite orbitRadius={4.4} orbitSpeed={0.002} inclination={1.2} />
        <ParticleField />
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 3, 5]} intensity={1.2} />
        <pointLight position={[-5, -3, -5]} intensity={0.2} color="#1D4ED8" />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={false} maxPolarAngle={Math.PI * 0.75} />
      </Suspense>
    </Canvas>
  )
}
