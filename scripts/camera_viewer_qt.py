#!/usr/bin/env python3
"""
ROS2 Camera Viewer with PyQt5
Gazebo simülasyonundan kamera görüntüsünü PyQt5 ile gösterir
"""

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap


class CameraSubscriber(Node):
    """ROS2 kamera görüntüsü subscriber"""
    
    def __init__(self, callback):
        super().__init__('camera_viewer')
        self.callback = callback
        self.bridge = CvBridge()
        
        # Kamera topic'ine abone ol
        self.subscription = self.create_subscription(
            Image,
            '/rover/camera/image_raw',
            self.image_callback,
            10
        )
        self.get_logger().info('Camera viewer başlatıldı. Topic: /rover/camera/image_raw')
        
    def image_callback(self, msg):
        """Kamera görüntüsü geldiğinde çağrılır"""
        try:
            # ROS Image mesajını OpenCV formatına çevir
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            # Qt callback'e gönder
            self.callback(cv_image)
        except Exception as e:
            self.get_logger().error(f'Görüntü dönüştürme hatası: {e}')


class CameraWindow(QMainWindow):
    """PyQt5 kamera görüntüleme penceresi"""
    
    # Signal tanımla
    update_image_signal = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Rover Kamera Görüntüsü')
        self.setGeometry(100, 100, 800, 600)
        
        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Görüntü için label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("border: 2px solid #4CAF50; background-color: black;")
        layout.addWidget(self.image_label)
        
        # Signal'ı slot'a bağla
        self.update_image_signal.connect(self.update_image)
        
        # ROS2 node'u başlat
        rclpy.init()
        self.ros_node = CameraSubscriber(self.on_image_received)
        
        # ROS2 spin için timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.spin_ros)
        self.timer.start(10)  # 10ms = 100Hz
        
    def on_image_received(self, cv_image):
        """ROS callback - Thread-safe signal gönder"""
        self.update_image_signal.emit(cv_image)
        
    def update_image(self, cv_image):
        """Qt UI'da görüntüyü güncelle"""
        # OpenCV BGR'den RGB'ye çevir
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # QImage oluştur
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # QPixmap'e çevir ve label'a set et
        pixmap = QPixmap.fromImage(qt_image)
        
        # Label boyutuna göre ölçekle (widget boyutuna sığdır)
        label_size = self.image_label.size()
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                label_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        
        
    def spin_ros(self):
        """ROS2 mesajlarını işle"""
        rclpy.spin_once(self.ros_node, timeout_sec=0)
        
    def closeEvent(self, event):
        """Pencere kapatılırken temizlik yap"""
        self.timer.stop()
        self.ros_node.destroy_node()
        rclpy.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CameraWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
