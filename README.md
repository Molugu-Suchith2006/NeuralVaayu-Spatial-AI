# NeuralVaayu: End-to-End Spatial Deep Learning & Computer Vision Interaction Engine

## 🚀 Abstract
**NeuralVaayu** is an advanced edge-AI spatial interaction framework built for real-time computer vision inference, gesture-driven automation, and low-latency peer-to-peer data bridging. By leveraging deep learning landmark estimation pipelines, multi-threaded asynchronous UI controllers, and socket-based network streaming, NeuralVaayu bridges physical hand kinematics with digital desktop workflows.

---

## 🧠 System Architecture & Core Pipelines

NeuralVaayu is engineered with a modular, decoupled three-tier architecture:

1. **Brain 1: AI Vision & Spatial Pipeline (`spatial_inference_engine.py`)**
   * Utilizes Google MediaPipe Hands model for high-precision 21-point 3D hand landmark coordinate regression.
   * Features dynamic Euclidean distance validation to define active interaction zones (`MIN_PALM_DISTANCE` to `MAX_PALM_DISTANCE`).
   * Implements real-time finger state classification (Open/Closed/Partial) to detect discrete custom gesture triggers.

2. **Brain 2: Asynchronous UI & Mascot Engine**
   * Operates on a separate multiprocessing queue layer using Tkinter.
   * Renders hardware-accelerated canvas animations, real-time LiDAR sweep wake/sleep visual feedback, and multi-stage payload glide animations.

3. **Brain 3: Network Bridge & P2P Streamer**
   * Implements custom TCP socket networking with 12-byte header parsing (`Msg Length`, `Original Width`, `Original Height`).
   * Features dynamic PIL image compression and Lanczos resampling to stream payloads across local networks with auto-retry resilience.

---

## 🛠️ Tech Stack & Dependencies
* **Python 3.x**
* **OpenCV (`cv2`)**: Real-time video frame capture and transformation.
* **MediaPipe**: Deep learning-based hand tracking and landmark extraction.
* **PyAutoGUI**: Native OS screen capture automation.
* **Pillow (`PIL`)**: High-performance image processing and tensor resizing.
* **Multiprocessing & Threading**: Concurrent execution for zero-lag UI responsiveness.

---

## ⚙️ Installation & Execution

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/Molugu-Suchith2006/NeuralVaayu-Spatial-AI.git](https://github.com/Molugu-Suchith2006/NeuralVaayu-Spatial-AI.git)
   cd NeuralVaayu-Spatial-AI

---

## 🌍 Socio-Technical Impact & SDG 9 Alignment
**NeuralVaayu** directly aligns with **United Nations Sustainable Development Goal 9 (SDG 9)**: *Build resilient infrastructure, promote inclusive and sustainable industrialization, and foster innovation.* 
* **Inclusive Industrialization:** By replacing traditional rigid 2D peripherals with touchless spatial interaction, NeuralVaayu advances human-computer interfaces for accessible, ergonomic, and next-generation industrial workflows.
* **Open Innovation:** The architecture provides a reproducible, lightweight edge-AI pipeline deployable on standard hardware without heavy cloud dependencies, democratizing spatial computing research.