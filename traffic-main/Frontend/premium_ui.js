/**
 * PREMIUM UI JAVASCRIPT
 * Adds Three.js particles and scroll animations without breaking existing logic.
 */

document.addEventListener("DOMContentLoaded", () => {
    initThreeJsBackground();
    initScrollAnimations();
    interceptRouteRendering();
});

function initThreeJsBackground() {
    const canvas = document.getElementById("three-canvas");
    if (!canvas) return;

    // Wait until THREE is loaded
    if (typeof THREE === "undefined") {
        setTimeout(initThreeJsBackground, 100);
        return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio > 1 ? 2 : 1);

    // Create particle network (City Nodes)
    const particleCount = window.innerWidth < 768 ? 100 : 300; // less particles on mobile
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const color1 = new THREE.Color(0x4F46E5); // Indigo
    const color2 = new THREE.Color(0x06B6D4); // Cyan

    for (let i = 0; i < particleCount; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 20;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 10 - 5;

        const mixRatio = Math.random();
        const mixedColor = color1.clone().lerp(color2, mixRatio);
        colors[i * 3] = mixedColor.r;
        colors[i * 3 + 1] = mixedColor.g;
        colors[i * 3 + 2] = mixedColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 0.08,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    camera.position.z = 5;

    let mouseX = 0;
    let mouseY = 0;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
    });

    function animate() {
        requestAnimationFrame(animate);

        // Only animate if canvas is visible (optimization)
        const landing = document.getElementById("landing");
        if (landing && landing.style.display !== "none") {
            particles.rotation.y += 0.001;
            particles.rotation.x += 0.0005;
            
            // Subtle parallax with mouse
            camera.position.x += (mouseX * 0.5 - camera.position.x) * 0.05;
            camera.position.y += (mouseY * 0.5 - camera.position.y) * 0.05;
            camera.lookAt(scene.position);

            renderer.render(scene, camera);
        }
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

function initScrollAnimations() {
    // Add reveal classes to specific elements
    const elementsToReveal = document.querySelectorAll('.feat-card-v2, .hiw-step, .stat-card, .testi-card');
    elementsToReveal.forEach(el => el.classList.add('reveal-up'));

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: "0px 0px -50px 0px" });

    elementsToReveal.forEach(el => observer.observe(el));
}

function interceptRouteRendering() {
    // We hook into the global displayRouteList function if it exists to add a smooth skeleton state first
    if (typeof window.displayRouteList === "function") {
        const originalDisplay = window.displayRouteList;
        window.displayRouteList = function(routes) {
            const list = document.getElementById('route-list');
            if (list) {
                // Show skeletons briefly for premium feel
                list.innerHTML = `
                    <div class="route-card skeleton-box" style="height: 120px; margin-bottom: 15px;"></div>
                    <div class="route-card skeleton-box" style="height: 120px;"></div>
                `;
                setTimeout(() => {
                    originalDisplay(routes);
                }, 400); // 400ms fake delay for smooth transition
            } else {
                originalDisplay(routes);
            }
        };
    }
}
