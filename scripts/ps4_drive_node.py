#!/usr/bin/env python3
"""
ROS 2 Rover Kontrolü için PS4 Kumanda Düğümü

Bu düğüm PS4 DualShock kumandadan /joy mesajlarını dinler ve
diff_drive_controller'a hız komutları gönderir.

Kontrol Şeması:
- R2 Tetik (Eksen 5): İleri gaz
- L2 Tetik (Eksen 4): Fren/Geri
- Sol Analog Çubuk Yatay (Eksen 0): Direksiyon
- X Butonu (Buton 0): Güvenlik düğmesi (sürüş için basılı tutulmalı)

Yazar: Bilgisayar Mühendisliği Öğrencisi
Lisans: Apache 2.0
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
import math


# PS4 Sürüş Düğümünü Tanımla


class PS4DriveNode(Node):
    """
    Rover kontrolü için özel PS4 kumanda sürücüsü.
    Tetik bazlı hızlanma ve analog direksiyon kontrolü.
    """

    def __init__(self):
        super().__init__('ps4_drive_node')
        
        # Parametreleri varsayılan değerlerle tanımla
        self.declare_parameter('max_linear_velocity', 2.5)  # m/s - maksimum ileri/geri hız
        self.declare_parameter('max_angular_velocity', 4.5)  # rad/s - maksimum dönüş hızı
        self.declare_parameter('deadman_button', 0)  # X butonu
        self.declare_parameter('enable_deadman', True)  # Güvenlik düğmesini etkinleştir/kapat
        self.declare_parameter('steering_axis', 0)  # Sol çubuk yatay ekseni
        self.declare_parameter('accelerator_axis', 5)  # R2 tetik
        self.declare_parameter('brake_axis', 4)  # L2 tetik
        self.declare_parameter('deadzone', 0.1)  # Joystick ölü bölge
        self.declare_parameter('trigger_deadzone', 0.02)  # Tetik ölü bölge
        self.declare_parameter('exponential_steering', True)  # Direksiyon için üstel eğri uygula
        self.declare_parameter('steering_sensitivity', 1.2)  # Direksiyon hassasiyeti çarpanı
        self.declare_parameter('invert_steering', False)  # Direksiyon yönünü tersine çevir
        self.declare_parameter('steering_power', 1.5)  # Üstel eğri kuvveti
        self.declare_parameter('steering_throttle_reduction', 0.5)  # Dönüşte gaz azaltma (0.0-1.0)
        self.declare_parameter('min_linear_scale', 0.3)  # Dönüşte minimum hız ölçeği
        self.declare_parameter('acceleration_curve_power', 1.3)  # Gaz pedalı için eğri uygula
        self.declare_parameter('brake_power', 2.0)  # Fren gücü
        self.declare_parameter('smoothing_enabled', True)  # Komut yumuşatmayı etkinleştir
        self.declare_parameter('smoothing_factor', 0.7)  # Yumuşatma faktörü (0.0-1.0)
        
        # Parametreleri al
        self.max_linear_vel = self.get_parameter('max_linear_velocity').value
        self.max_angular_vel = self.get_parameter('max_angular_velocity').value
        self.deadman_button = self.get_parameter('deadman_button').value
        self.enable_deadman = self.get_parameter('enable_deadman').value
        self.steering_axis = self.get_parameter('steering_axis').value
        self.accelerator_axis = self.get_parameter('accelerator_axis').value
        self.brake_axis = self.get_parameter('brake_axis').value
        self.deadzone = self.get_parameter('deadzone').value
        self.trigger_deadzone = self.get_parameter('trigger_deadzone').value
        self.exponential_steering = self.get_parameter('exponential_steering').value
        self.steering_sensitivity = self.get_parameter('steering_sensitivity').value
        self.invert_steering = self.get_parameter('invert_steering').value
        self.steering_power = self.get_parameter('steering_power').value
        self.steering_throttle_reduction = self.get_parameter('steering_throttle_reduction').value
        self.min_linear_scale = self.get_parameter('min_linear_scale').value
        self.acceleration_curve_power = self.get_parameter('acceleration_curve_power').value
        self.brake_power = self.get_parameter('brake_power').value
        self.smoothing_enabled = self.get_parameter('smoothing_enabled').value
        self.smoothing_factor = self.get_parameter('smoothing_factor').value
        
        # Yumuşatma için son komutu sakla
        self.last_linear_x = 0.0
        self.last_angular_z = 0.0
        
        # Joy topicine abone ol
        self.joy_sub = self.create_subscription(
            Joy,
            '/joy',
            self.joy_callback,
            10
        )
        
        # Hız komutları için yayıncı oluştur (diff_drive_controller için unstamped)
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/diff_drive_controller/cmd_vel_unstamped',
            10
        )
        
        # Zaman aşımı tespiti için son komut zamanını başlat
        self.last_joy_time = self.get_clock().now()
        
        # Koruma zamanlayıcısı oluştur (joy mesajı gelmezse rover'ı durdur)
        self.watchdog_timer = self.create_timer(0.1, self.watchdog_callback)
        self.watchdog_timeout = 1.0  # saniye
        
        self.get_logger().info('PS4 Kumanda Kontrolü Başlatıldı')
        self.get_logger().info(f'Maksimum Doğrusal Hız: {self.max_linear_vel} m/s')
        self.get_logger().info(f'Maksimum Açısal Hız: {self.max_angular_vel} rad/s')
        self.get_logger().info(f'Direksiyon Hassasiyeti: {self.steering_sensitivity}x')
        self.get_logger().info(f'Güvenlik Düğmesi: {"Etkin" if self.enable_deadman else "Devre Dışı"} (Buton {self.deadman_button})')
        self.get_logger().info('Kontroller: R2=Gaz, L2=Fren/Geri, Sol Çubuk=Direksiyon, X=Güvenlik')

    def apply_deadzone(self, value, deadzone):
        """
        Joystick/tetik değerlerine ölü bölge uygula.
        Ölü bölge içindeki değerler 0.0 döndürür.
        """
        if abs(value) < deadzone:
            return 0.0
        # Kalan aralığı ölçeklendir (düzgün kontrol için)
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - deadzone) / (1.0 - deadzone)

    def normalize_trigger(self, trigger_value):
        """
        PS4 tetik değerini [-1.0, 1.0] aralığından [0.0, 1.0] aralığına normalize et.
        PS4 tetikler bırakıldığında -1.0, tam basıldığında 1.0 değeri okur.
        """
        # [-1, 1] aralığından [0, 1] aralığına dönüştür
        normalized = (trigger_value + 1.0) / 2.0
        return max(0.0, min(1.0, normalized))  # [0, 1] aralığına sınırla

    def apply_exponential_curve(self, value, power=2.0):
        """
        Düşük hızlarda daha hassas kontrol için üstel eğri uygula.
        Girdi işaretini korur. Düşük güç = daha doğrusal, yüksek = daha hassas.
        """
        sign = 1.0 if value >= 0 else -1.0
        return sign * (abs(value) ** power)
    
    def smooth_command(self, new_value, last_value, factor=0.7):
        """
        Komutlara üstel yumuşatma uygula.
        factor: 0.0 = tam yumuşatma (çok yavaş), 1.0 = yumuşatma yok (hızlı tepki)
        """
        return factor * new_value + (1.0 - factor) * last_value

    def joy_callback(self, msg: Joy):
        """
        Joystick girdisini işle ve hız komutlarını yayınla.
        """
        # Son mesaj zamanını güncelle
        self.last_joy_time = self.get_clock().now()
        
        # Güvenlik düğmesini kontrol et (etkinse)
        if self.enable_deadman:
            if len(msg.buttons) <= self.deadman_button or msg.buttons[self.deadman_button] == 0:
                # Güvenlik düğmesine basılmamış, rover'ı durdur
                self.publish_stop_command()
                self.last_linear_x = 0.0
                self.last_angular_z = 0.0
                return
        
        # Twist mesajını başlat
        twist = Twist()
        
        # Tetik değerlerini al ve normalize et
        linear_x = 0.0
        if len(msg.axes) > max(self.accelerator_axis, self.brake_axis):
            # Ham tetik değerlerini al
            accelerator_raw = msg.axes[self.accelerator_axis]
            brake_raw = msg.axes[self.brake_axis]
            
            # Tetikleri [-1, 1] aralığından [0, 1] aralığına normalize et
            accelerator = self.normalize_trigger(accelerator_raw)
            brake = self.normalize_trigger(brake_raw)
            
            # Tetik ölü bölgesini uygula
            accelerator = self.apply_deadzone(accelerator, self.trigger_deadzone)
            brake = self.apply_deadzone(brake, self.trigger_deadzone)
            
            # Hızlanma eğrileri uygula
            if accelerator > 0:
                accelerator = self.apply_exponential_curve(accelerator, power=self.acceleration_curve_power)
            if brake > 0:
                brake = self.apply_exponential_curve(brake, power=self.brake_power)
            
            # Doğrusal hızı hesapla (ileri - geri)
            # R2 (gaz) = pozitif (ileri)
            # L2 (fren) = negatif (geri)
            linear_x = (accelerator - brake) * self.max_linear_vel
        else:
            self.get_logger().warn('Tetik eksenleri mevcut değil, joy sürücü ayarlarını kontrol edin')
        
        # Sol analog çubuktan (yatay) direksiyon girdisini al
        angular_z = 0.0
        if len(msg.axes) > self.steering_axis:
            steering_raw = msg.axes[self.steering_axis]
            if self.invert_steering:
                steering_raw *= -1.0
            
            # Ölü bölge uygula
            steering = self.apply_deadzone(steering_raw, self.deadzone)
            
            # Üstel eğri uygula (etkinse)
            if self.exponential_steering and steering != 0.0:
                steering = self.apply_exponential_curve(steering, power=self.steering_power)
            
            # Hassasiyet çarpanını uygula
            steering *= self.steering_sensitivity
            
            # Açısal hızı hesapla (sol çubuk dönüşü kontrol eder)
            angular_z = steering * self.max_angular_vel
            
            # Direksiyon kırılırken gaz azaltma
            # Virajlarda hızı korur
            if self.steering_throttle_reduction > 0.0 and linear_x != 0.0:
                # Sadece hareket ederken gazı azalt
                reduction = abs(steering) * self.steering_throttle_reduction
                scale = max(self.min_linear_scale, 1.0 - reduction)
                linear_x *= scale
        else:
            self.get_logger().warn('Direksiyon ekseni mevcut değil')

        # Apply command smoothing for arcade feel
        if self.smoothing_enabled:
            linear_x = self.smooth_command(linear_x, self.last_linear_x, self.smoothing_factor)
            angular_z = self.smooth_command(angular_z, self.last_angular_z, self.smoothing_factor)
        
        # Store for next iteration
        self.last_linear_x = linear_x
        self.last_angular_z = angular_z

        twist.linear.x = linear_x
        twist.angular.z = angular_z
        
        # Publish the velocity command
        self.cmd_vel_pub.publish(twist)
        
        # Log current command (throttled to avoid spam)
        if abs(twist.linear.x) > 0.01 or abs(twist.angular.z) > 0.01:
            self.get_logger().debug(
                f'CMD: linear.x={twist.linear.x:.2f} m/s, angular.z={twist.angular.z:.2f} rad/s'
            )

    def publish_stop_command(self):
        """
        Rover'ı durdurmak için sıfır hız komutu yayınla.
        """
        twist = Twist()
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)

    def watchdog_callback(self):
        """
        Joystick mesajı alınmazsa rover'ı durduran koruma zamanlayıcısı.
        Güvenlik özelliği - kontrolsüz hareket önleme.
        """
        time_since_last_joy = (self.get_clock().now() - self.last_joy_time).nanoseconds / 1e9
        
        if time_since_last_joy > self.watchdog_timeout:
            # Joystick mesajı uzun süredir alınmadı, rover'ı durdur
            self.publish_stop_command()
            # Her zaman aşımı periyodunda sadece bir kere logla
            if time_since_last_joy < self.watchdog_timeout + 0.2:
                self.get_logger().warn('Joystick zaman aşımı - rover durduruluyor')


def main(args=None):
    """
    PS4 sürüş düğümü için ana giriş noktası.
    """
    rclpy.init(args=args)
    
    try:
        node = PS4DriveNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'PS4 sürüş düğümünde hata: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
