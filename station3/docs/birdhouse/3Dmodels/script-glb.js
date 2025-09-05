import * as THREE from 'three'; //three.js-master/build/three.module.min.js
import { GLTFLoader } from './GLTFLoader.js'; //'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from './OrbitControls.js';
// Create a scene, camera, and renderer
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// 1. Set background color
scene.background = new THREE.Color(0xcccccc);  // Light grey background
//const txloader = new THREE.TextureLoader();
//txloader.load('./clouds640.jpg', (texture) => {
//  scene.background = texture;
//});

// 2. Enable shadow rendering
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap; // Optional: for softer shadows

// Add lights to the scene
const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(10, 30, 10);
directionalLight.castShadow = true;
scene.add(directionalLight);

// Create a GLTFLoader instance
const loader = new GLTFLoader();
const controls = new OrbitControls(camera, renderer.domElement);
controls.update();

// Load the .glb file birdhouse3D.glb collision-world.glb
loader.load(
  './birdhouse3D.glb',
  (gltf) => {
    // Add the loaded model to the scene
    const model = gltf.scene;
    scene.add(model);
    let scalefact = 3.0;
    model.scale.set(scalefact,scalefact,scalefact);
    model.rotation.set(0, -Math.PI/4, 0);
    //model.position.set(0, 0, 0);
    
    // Adjust camera position if needed
    camera.position.set(0, 0, 100);
    },
  (progress) => {
    console.log(`Loading: ${(progress.loaded / progress.total) * 100}%`);
  },
  (error) => {
    console.error('An error occurred while loading the model:', error);
  }
);

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();