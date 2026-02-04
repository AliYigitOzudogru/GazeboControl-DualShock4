# Rover Kamera Kullanımı

## Kamera Özellikleri
- **Çözünürlük**: 640x480 piksel
- **FPS**: 30 Hz
- **FOV**: 60 derece (1.047 radyan)
- **ROS2 Topic**: `/rover/camera/image_raw`
- **Mesaj Tipi**: `sensor_msgs/msg/Image`

## Kurulum

### Gerekli Python Paketleri
```bash
pip install PyQt5 opencv-python
sudo apt install ros-humble-cv-bridge  # ROS2 Humble için
```

## Kullanım Seçenekleri

### Seçenek 1: Hazır Kamera Görüntüleyici

Bağımsız kamera görüntüleyici uygulaması:

```bash
# Gazebo simülasyonunu başlat
ros2 launch rover_sim simulation.launch.py

# Başka bir terminalde kamera görüntüleyiciyi çalıştır
cd ~/Desktop/projects/GazeboControl-DualShock4
python3 scripts/camera_viewer_qt.py
```

### Seçenek 2: Kendi Qt Uygulamanıza Entegrasyon

`camera_widget.py` dosyasındaki `RoverCameraWidget` sınıfını kullanabilirsiniz:

```python
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import rclpy
from camera_widget import RoverCameraWidget

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Rover Kontrol Paneli')
        
        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Kamera widget'ını ekle
        self.camera = RoverCameraWidget()
        layout.addWidget(self.camera)
        
        # Diğer kontrollerinizi buraya ekleyin...
        
    def showEvent(self, event):
        """Pencere açıldığında kamerayı başlat"""
        super().showEvent(event)
        rclpy.init()
        self.camera.start()
    
    def closeEvent(self, event):
        """Pencere kapanırken temizlik"""
        self.camera.stop()
        rclpy.shutdown()
        event.accept()

if __name__ == '__main__':
    app = QApplication([])
    window = MyApp()
    window.show()
    app.exec_()
```

### Seçenek 3: OpenCV ile Basit Görüntüleme

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class SimpleCameraViewer(Node):
    def __init__(self):
        super().__init__('simple_viewer')
        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image,
            '/rover/camera/image_raw',
            self.callback,
            10)
    
    def callback(self, msg):
        cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        cv2.imshow('Rover Camera', cv_image)
        cv2.waitKey(1)

def main():
    rclpy.init()
    viewer = SimpleCameraViewer()
    rclpy.spin(viewer)
    cv2.destroyAllWindows()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Kamera Topic'lerini Kontrol Etme

```bash
# Aktif topic'leri listele
ros2 topic list

# Kamera mesajlarını görüntüle
ros2 topic echo /rover/camera/image_raw

# Kamera bilgilerini kontrol et
ros2 topic info /rover/camera/image_raw

# Kamera görüntüsünü kaydet
ros2 run image_tools showimage --ros-args -r image:=/rover/camera/image_raw
```

## Kamera Pozisyonunu Değiştirme

Kamera konumunu değiştirmek için [rover.urdf.xacro](urdf/rover.urdf.xacro) dosyasındaki şu satırı düzenleyin:

```xml
<joint name="camera_joint" type="fixed">
  <origin xyz="0.25 0 0.05" rpy="0 0 0" />
  <!-- xyz: x=ileri/geri, y=sağ/sol, z=yukarı/aşağı -->
  <!-- rpy: roll, pitch, yaw (radyan) -->
  <parent link="base_link" />
  <child link="camera_link" />
</joint>
```

Değişiklikten sonra paketi yeniden derleyin:
```bash
cd ~/Desktop/projects/GazeboControl-DualShock4
colcon build
source install/setup.bash
```

## Sorun Giderme

### Kamera görüntüsü gelmiyor
```bash
# Gazebo'da kamera sensörünün aktif olduğunu kontrol edin
gz topic -l | grep camera

# Topic'in yayın yaptığını doğrulayın
ros2 topic hz /rover/camera/image_raw
```

### cv_bridge hatası
```bash
# cv_bridge'i yeniden kurun
sudo apt install ros-humble-cv-bridge
```

### PyQt5 hatası
```bash
pip install --upgrade PyQt5
```

## Gelişmiş Özellikler

### Görüntü Kaydetme
Widget'a görüntü kaydetme fonksiyonu ekleyebilirsiniz:

```python
def save_image(self, cv_image):
    import time
    filename = f"rover_camera_{int(time.time())}.jpg"
    cv2.imwrite(filename, cv_image)
    print(f"Görüntü kaydedildi: {filename}")
```

### Görüntü İşleme
Kamera görüntüsü üzerinde işlem yapabilirsiniz:

```python
def _update_display(self, cv_image):
    # Örnek: Kenar tespiti
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    
    # Orijinal görüntü üzerine çiz
    cv_image[edges > 0] = [0, 255, 0]
    
    # Normal display işlemi...
```
