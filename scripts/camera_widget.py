#!/usr/bin/env python3
"""
ROS2 Camera Widget - Kendi Qt uygulamanıza ekleyebilirsiniz
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap


class RoverCameraWidget(QLabel):
    """
    Rover kamerasını gösteren Qt Widget
    
    Kullanım:
        # Ana uygulamanızda:
        from camera_widget import RoverCameraWidget
        
        # Widget'ı layout'a ekle
        self.camera_widget = RoverCameraWidget()
        self.layout.addWidget(self.camera_widget)
        
        # ROS2'yi başlat (uygulamanızın başında bir kere)
        rclpy.init()
        
        # Widget'ı başlat
        self.camera_widget.start()
        
        # Uygulamanız kapanırken
        self.camera_widget.stop()
        rclpy.shutdown()
    """
    
    # Signal
    image_received = pyqtSignal(np.ndarray)
    
    def __init__(self, parent=None, topic='/rover/camera/image_raw'):
        super().__init__(parent)
        
        self.topic = topic
        self.ros_node = None
        self.timer = None
        self.bridge = CvBridge()
        
        # Widget görünümü
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid #2196F3; background-color: #000000;")
        self.setMinimumSize(320, 240)
        self.setText('Kamera bağlanıyor...')
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #2196F3;
                background-color: #000000;
                color: #FFFFFF;
                font-size: 14px;
            }
        """)
        
        # Signal bağlantısı
        self.image_received.connect(self._update_display)
        
    def start(self):
        """Kamera akışını başlat"""
        if self.ros_node is None:
            # ROS2 node oluştur
            self.ros_node = Node('camera_widget_node')
            
            # Kamera topic'ine abone ol
            self.subscription = self.ros_node.create_subscription(
                Image,
                self.topic,
                self._image_callback,
                10
            )
            
            # ROS2 spin timer
            self.timer = QTimer()
            self.timer.timeout.connect(self._spin_ros)
            self.timer.start(10)  # 100Hz
            
            print(f'Kamera widget başlatıldı. Topic: {self.topic}')
    
    def stop(self):
        """Kamera akışını durdur"""
        if self.timer:
            self.timer.stop()
        if self.ros_node:
            self.ros_node.destroy_node()
            self.ros_node = None
        print('Kamera widget durduruldu.')
    
    def _image_callback(self, msg):
        """ROS callback - görüntü geldiğinde"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.image_received.emit(cv_image)
        except Exception as e:
            print(f'Görüntü hatası: {e}')
    
    def _update_display(self, cv_image):
        """Görüntüyü ekranda göster"""
        # BGR -> RGB
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # QImage oluştur
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Widget boyutuna göre ölçekle
        widget_size = self.size()
        if widget_size.width() > 0 and widget_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                widget_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
    
    def _spin_ros(self):
        """ROS mesajlarını işle"""
        if self.ros_node:
            rclpy.spin_once(self.ros_node, timeout_sec=0)


# === ÖRNEK KULLANIM ===
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('Rover Kamera Test')
            self.setGeometry(100, 100, 800, 600)
            
            # Ana widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Kamera widget ekle
            self.camera = RoverCameraWidget()
            layout.addWidget(self.camera)
            
            # Kontrol butonu
            btn = QPushButton('Durdur/Başlat')
            btn.clicked.connect(self.toggle_camera)
            layout.addWidget(btn)
            
            self.camera_running = False
            
        def showEvent(self, event):
            """Pencere gösterildiğinde kamerayı başlat"""
            super().showEvent(event)
            if not self.camera_running:
                rclpy.init()
                self.camera.start()
                self.camera_running = True
        
        def toggle_camera(self):
            if self.camera_running:
                self.camera.stop()
                self.camera_running = False
            else:
                self.camera.start()
                self.camera_running = True
                
        def closeEvent(self, event):
            self.camera.stop()
            rclpy.shutdown()
            event.accept()
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
