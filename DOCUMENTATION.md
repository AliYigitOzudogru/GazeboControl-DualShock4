# 🚗 Rover Simulation - Kapsamlı Dokümantasyon

## 📋 İçindekiler
1. [Proje Genel Bakış](#proje-genel-bakış)
2. [Sistem Mimarisi](#sistem-mimarisi)
3. [Dosya Yapısı ve Hiyerarşi](#dosya-yapısı-ve-hiyerarşi)
4. [Bileşenler ve Bağlantılar](#bileşenler-ve-bağlantılar)
5. [ROS 2 Topic ve Node Yapısı](#ros-2-topic-ve-node-yapısı)
6. [URDF/Xacro Yapısı](#urdfxacro-yapısı)
7. [Controller Konfigürasyonu](#controller-konfigürasyonu)
8. [PS4 Kontrolcü Entegrasyonu](#ps4-kontrolcü-entegrasyonu)
9. [Karşılaşılan Hatalar ve Çözümleri](#karşılaşılan-hatalar-ve-çözümleri)
10. [Kullanım Kılavuzu](#kullanım-kılavuzu)

---

## 🎯 Proje Genel Bakış

Bu proje, ROS 2 Humble ve Gazebo Sim (Ignition Fortress) kullanarak bir rover simülasyonu oluşturur. Rover, PS4 DualShock 4 kontrolcüsü ile süspansiyonlu 4 tekerlekli diferansiyel sürüş sistemiyle kontrol edilebilir.

### Kullanılan Teknolojiler
- **ROS 2 Humble** - Robot Operating System
- **Gazebo Sim (Ignition Fortress)** - Fizik simülatörü
- **ros2_control** - Robot kontrolcü framework'ü
- **gz_ros2_control** - Gazebo-ROS2 control köprüsü
- **joy** - Joystick/Gamepad driver
- **xacro** - XML macro işlemcisi

---

## 🏗️ Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KULLANICI GİRİŞİ                               │
│                     ┌─────────────────────┐                              │
│                     │   PS4 DualShock 4   │                              │
│                     │    Kontrolcüsü      │                              │
│                     └──────────┬──────────┘                              │
│                                │ /dev/input/js1                          │
│                                ▼                                         │
│                     ┌─────────────────────┐                              │
│                     │     joy_node        │                              │
│                     │  (sensor_msgs/Joy)  │                              │
│                     └──────────┬──────────┘                              │
│                                │ /joy                                    │
│                                ▼                                         │
│                     ┌─────────────────────┐                              │
│                     │  ps4_drive_node.py  │                              │
│                     │  (Özel Python Node) │                              │
│                     └──────────┬──────────┘                              │
│                                │ /diff_drive_controller/cmd_vel_unstamped│
│                                ▼                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         ROS 2 CONTROL LAYER                              │
│                     ┌─────────────────────┐                              │
│                     │ diff_drive_controller│                              │
│                     │  (Velocity → Wheel) │                              │
│                     └──────────┬──────────┘                              │
│                                │ wheel velocity commands                 │
│                                ▼                                         │
│                     ┌─────────────────────┐                              │
│                     │ joint_state_broadcaster                            │
│                     │  (Joint States)     │                              │
│                     └──────────┬──────────┘                              │
│                                │                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         GAZEBO SIM LAYER                                 │
│                     ┌─────────────────────┐                              │
│                     │  GazeboSimSystem    │                              │
│                     │ (gz_ros2_control)   │                              │
│                     └──────────┬──────────┘                              │
│                                │                                         │
│                                ▼                                         │
│                     ┌─────────────────────┐                              │
│                     │   Gazebo Physics    │                              │
│                     │   (DART Engine)     │                              │
│                     └──────────┬──────────┘                              │
│                                │                                         │
│                                ▼                                         │
│                     ┌─────────────────────┐                              │
│                     │    ROVER MODEL      │                              │
│                     │  (URDF + Meshes)    │                              │
│                     └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Dosya Yapısı ve Hiyerarşi

```
rover_sim/
├── CMakeLists.txt              # Derleme konfigürasyonu
├── package.xml                 # ROS 2 paket manifest
├── model.config                # Gazebo model konfigürasyonu
│
├── config/
│   └── controllers.yaml        # ros2_control controller ayarları
│
├── launch/
│   ├── simulation.launch.py    # Ana launch dosyası (tüm sistemi başlatır)
│   ├── gazebo.launch           # Sadece Gazebo launch (eski format)
│   └── display.launch          # RViz görselleştirme
│
├── urdf/
│   ├── rover.urdf.xacro        # Ana robot tanımı (Xacro format)
│   └── gövde Urdf Montajı.urdf # Orijinal SolidWorks çıktısı
│
├── meshes/                     # 3D model dosyaları (STL)
│   ├── base_link.STL
│   ├── Sag_suspansiyon_merkezi.STL
│   ├── Sag_On.STL
│   ├── Sag_Arka.STL
│   ├── Sol_Suspensiyon_merkezi.STL
│   ├── Sol_On.STL
│   └── Sol_Arka.STL
│
├── scripts/
│   └── ps4_drive_node.py       # PS4 kontrolcü → cmd_vel dönüştürücü
│
├── worlds/
│   └── rover_world.sdf         # Gazebo dünya dosyası
│
├── textures/                   # Texture dosyaları (varsa)
│
├── build/                      # Derleme çıktıları
├── install/                    # Kurulum dosyaları
└── log/                        # Log dosyaları
```

---

## 🔗 Bileşenler ve Bağlantılar

### 1. Launch Sistemi (simulation.launch.py)

```python
# Başlatılan bileşenler sırası:
1. Environment Variables (GZ_SIM_RESOURCE_PATH)
2. Gazebo Sim
3. robot_state_publisher
4. spawn_robot (rover'ı Gazebo'ya ekler)
5. joint_state_broadcaster (spawn sonrası)
6. diff_drive_controller (joint_state_broadcaster sonrası)
7. ros_gz_bridge (clock, odometry)
8. joy_node
9. ps4_drive_node.py
```

### 2. URDF Link Hiyerarşisi

```
base_link (Gövde)
├── Sag_suspansiyon_merkezi (Sağ Süspansiyon)
│   ├── right_front_wheel (Sağ Ön Tekerlek)
│   └── right_rear_wheel (Sağ Arka Tekerlek)
│
└── Sol_Suspensiyon_merkezi (Sol Süspansiyon)
    ├── left_front_wheel (Sol Ön Tekerlek)
    └── left_rear_wheel (Sol Arka Tekerlek)
```

### 3. Joint Tipleri

| Joint Adı | Tip | Parent → Child | Eksen |
|-----------|-----|----------------|-------|
| Sag_Suspansiyon_merkezi_joint | revolute | base_link → Sag_suspansiyon_merkezi | Y |
| Sol_Suspensiyon_merkezi_joint | revolute | base_link → Sol_Suspensiyon_merkezi | Y |
| right_front_wheel_joint | continuous | Sag_suspansiyon_merkezi → right_front_wheel | Y |
| right_rear_wheel_joint | continuous | Sag_suspansiyon_merkezi → right_rear_wheel | Y |
| left_front_wheel_joint | continuous | Sol_Suspensiyon_merkezi → left_front_wheel | Y |
| left_rear_wheel_joint | continuous | Sol_Suspensiyon_merkezi → left_rear_wheel | Y |

---

## 📡 ROS 2 Topic ve Node Yapısı

### Aktif Node'lar

| Node Adı | Paket | Görevi |
|----------|-------|--------|
| joy_node | joy | PS4 kontrolcü verilerini okur |
| ps4_drive_node | rover_sim | Joy → Twist dönüşümü |
| robot_state_publisher | robot_state_publisher | URDF yayınlar, TF broadcast |
| controller_manager | controller_manager | Controller lifecycle yönetimi |
| joint_state_broadcaster | joint_state_broadcaster | Joint state yayını |
| diff_drive_controller | diff_drive_controller | Diferansiyel sürüş kontrolü |

### Topic Akışı

```
/joy (sensor_msgs/Joy)
    │
    └──► ps4_drive_node
            │
            └──► /diff_drive_controller/cmd_vel_unstamped (geometry_msgs/Twist)
                    │
                    └──► diff_drive_controller
                            │
                            ├──► Tekerlek velocity komutları (Gazebo'ya)
                            │
                            └──► /diff_drive_controller/odom (nav_msgs/Odometry)
```

### Önemli Topic'ler

| Topic | Mesaj Tipi | Yayıncı | Abone |
|-------|-----------|---------|-------|
| /joy | sensor_msgs/Joy | joy_node | ps4_drive_node |
| /diff_drive_controller/cmd_vel_unstamped | geometry_msgs/Twist | ps4_drive_node | diff_drive_controller |
| /joint_states | sensor_msgs/JointState | joint_state_broadcaster | robot_state_publisher |
| /tf | tf2_msgs/TFMessage | robot_state_publisher | - |
| /clock | rosgraph_msgs/Clock | ros_gz_bridge | Tüm node'lar |

---

## 🤖 URDF/Xacro Yapısı

### Mesh Dosyası Referans Formatı

```xml
<!-- Doğru format (file:// + $(find package)) -->
<mesh filename="file://$(find rover_sim)/meshes/base_link.STL" />
```

### ros2_control Konfigürasyonu (URDF içinde)

```xml
<ros2_control name="GazeboSystem" type="system">
  <hardware>
    <plugin>gz_ros2_control/GazeboSimSystem</plugin>
  </hardware>
  
  <!-- Her tekerlek joint'i için -->
  <joint name="right_front_wheel_joint">
    <command_interface name="velocity">
      <param name="min">-10</param>
      <param name="max">10</param>
    </command_interface>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
  <!-- ... diğer joint'ler ... -->
</ros2_control>

<gazebo>
  <plugin filename="gz_ros2_control-system" 
          name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find rover_sim)/config/controllers.yaml</parameters>
  </plugin>
</gazebo>
```

---

## ⚙️ Controller Konfigürasyonu

### controllers.yaml

```yaml
controller_manager:
  ros__parameters:
    update_rate: 50  # Hz

diff_drive_controller:
  ros__parameters:
    # Tekerlek isimleri
    left_wheel_names: ["left_front_wheel_joint", "left_rear_wheel_joint"]
    right_wheel_names: ["right_front_wheel_joint", "right_rear_wheel_joint"]
    
    # Fiziksel parametreler
    wheel_separation: 0.51  # Tekerlekler arası mesafe (m)
    wheel_radius: 0.1       # Tekerlek yarıçapı (m)
    
    # Önemli: Unstamped velocity kullanımı
    use_stamped_vel: false
    
    # Hız limitleri
    linear.x.max_velocity: 2.0   # m/s
    angular.z.max_velocity: 3.0  # rad/s
```

---

## 🎮 PS4 Kontrolcü Entegrasyonu

### Kontrol Şeması

```
┌─────────────────────────────────────────┐
│            PS4 DualShock 4              │
│                                         │
│    [L2]                      [R2]       │
│    Geri                      İleri      │
│                                         │
│         ┌───┐        ┌───┐              │
│         │   │        │   │              │
│    ┌────┤   ├────┐   │   │              │
│    │    └───┘    │   └───┘              │
│    │  Sol Analog │   Sağ Analog         │
│    │  (Direksiyon)   (Kullanılmıyor)    │
│    └─────────────┘                      │
│                                         │
│    [X] Deadman Switch (basılı tutulmalı)│
│                                         │
└─────────────────────────────────────────┘
```

### ps4_drive_node.py Parametreleri

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| max_linear_velocity | 2.0 m/s | Maksimum ileri/geri hız |
| max_angular_velocity | 3.0 rad/s | Maksimum dönüş hızı |
| deadman_button | 0 (X butonu) | Güvenlik butonu |
| steering_axis | 0 | Sol analog yatay eksen |
| accelerator_axis | 5 | R2 trigger |
| brake_axis | 4 | L2 trigger |
| deadzone | 0.25 | Analog stick drift önleme |
| trigger_deadzone | 0.05 | Trigger deadzone |

### Axis Mapping (joy_node)

```
axes[0] = Sol Analog Yatay (Direksiyon)
axes[1] = Sol Analog Dikey
axes[2] = Sağ Analog Yatay
axes[3] = Sağ Analog Dikey
axes[4] = L2 Trigger (-1.0 = bırakılmış, 1.0 = basılı)
axes[5] = R2 Trigger (-1.0 = bırakılmış, 1.0 = basılı)

buttons[0] = X (Deadman)
buttons[1] = O
buttons[2] = △
buttons[3] = □
```

---

## 🐛 Karşılaşılan Hatalar ve Çözümleri

### 1. Mesh Dosyaları Bulunamıyor

**Hata:**
```
[Err] Unable to find file with URI [model://rover_sim/meshes/base_link.STL]
```

**Sebep:** Gazebo `package://` URI şemasını anlamıyor.

**Çözüm:** URDF'de mesh path'lerini `file://$(find rover_sim)` formatına değiştir:
```xml
<!-- Yanlış -->
<mesh filename="package://rover_sim/meshes/base_link.STL" />

<!-- Doğru -->
<mesh filename="file://$(find rover_sim)/meshes/base_link.STL" />
```

---

### 2. Yanlış Paket Adı

**Hata:**
```
[Err] Unable to find file with URI [package://gövde Urdf Montajı/meshes/...]
```

**Sebep:** SolidWorks URDF exporter Türkçe karakterli paket adı oluşturmuş.

**Çözüm:** Tüm mesh referanslarını `rover_sim` paket adına değiştir:
```bash
sed -i 's|package://gövde Urdf Montajı/meshes/|package://rover_sim/meshes/|g' urdf/rover.urdf.xacro
```

---

### 3. Mesh Dosya Adlarında Boşluk

**Hata:**
```
[Err] Unable to find file [model://rover_sim/meshes/Sag Arka.STL]
```

**Sebep:** Dosya adlarında boşluk Gazebo'da sorun yaratıyor.

**Çözüm:** Dosya adlarını yeniden adlandır:
```bash
mv 'Sag Arka.STL' 'Sag_Arka.STL'
mv 'Sol Suspensiyon merkezi.STL' 'Sol_Suspensiyon_merkezi.STL'
# ... diğerleri
```

---

### 4. Joy Node Yanlış Cihazı Kullanıyor

**Hata:**
```
[joy_node] Opened joystick: Keychron Keychron Link
```

**Sebep:** Sistem birden fazla joystick cihazı algılıyor (js0 = klavye, js1 = PS4).

**Çözüm:** `device_id` parametresini ayarla:
```python
# launch/simulation.launch.py içinde
joy_node = Node(
    package='joy',
    executable='joy_node',
    parameters=[{
        'device_id': 1,  # js1 = PS4 controller
    }],
)
```

---

### 5. Controller cmd_vel Dinlemiyor

**Hata:**
```
Topic: /diff_drive_controller/cmd_vel_unstamped
Subscription count: 0
```

**Sebep:** `use_stamped_vel` parametresi ayarlanmamış.

**Çözüm:** `controllers.yaml`'a ekle:
```yaml
diff_drive_controller:
  ros__parameters:
    use_stamped_vel: false  # Unstamped Twist mesajları kullan
```

---

### 6. Tekerlekler Yerin Altında

**Hata:** Robot spawn edildiğinde tekerlekler zemine gömülü.

**Sebep:** Spawn yüksekliği (z) çok düşük.

**Çözüm:** `simulation.launch.py`'da spawn yüksekliğini artır:
```python
spawn_robot = Node(
    arguments=[
        '-z', '1.0',  # 0.5'ten 1.0'a çıkarıldı
    ],
)
```

---

### 7. Joystick Drift (Kendiliğinden Dönme)

**Hata:** R2 basılıyken rover yavaşça dönüyor.

**Sebep:** Sol analog stick tam merkezde durmuyor (hardware sorunu).

**Çözüm:** Deadzone değerini artır:
```python
self.declare_parameter('deadzone', 0.25)  # 0.1'den 0.25'e
```

---

### 8. Sol ve Sağ Tekerlekler Zıt Yönde Dönüyor

**Hata:** İleri giderken sol tekerlekler geriye, sağ tekerlekler ileriye dönüyor.

**Sebep:** URDF'de sol tekerlek eksen yönü `-Y`, sağ tekerlek `+Y`.

**Çözüm:** Tüm tekerlekleri aynı eksen yönüne ayarla:
```xml
<!-- Tüm tekerlekler için aynı eksen -->
<axis xyz="0 1 0" />
```

---

### 9. GZ_SIM_RESOURCE_PATH Sorunu

**Hata:** Gazebo mesh ve model dosyalarını bulamıyor.

**Çözüm:** Launch dosyasında environment variable ayarla:
```python
pkg_share_parent = os.path.dirname(pkg_share)
gazebo_model_path = SetEnvironmentVariable(
    name='GZ_SIM_RESOURCE_PATH',
    value=pkg_share_parent + ':' + pkg_share
)
```

---

### 10. Entity Already Exists

**Hata:**
```
[Err] Entity named [rover] already exists
```

**Sebep:** Önceki simülasyondan rover hala bellekte.

**Çözüm:** Gazebo'yu tamamen kapat ve yeniden başlat:
```bash
pkill -9 -f "gz sim"
pkill -9 -f "ign gazebo"
# Sonra simülasyonu yeniden başlat
```

---

## 🚀 Kullanım Kılavuzu

### Hızlı Başlangıç

```bash
# 1. Terminal - Simülasyon
cd ~/Desktop/tunay_sonurdf/URDF/rover_sim
colcon build --symlink-install
source install/setup.bash
ros2 launch rover_sim simulation.launch.py

# 2. Terminal - PS4 Kontrolcü (opsiyonel, launch'ta dahil)
source ~/Desktop/tunay_sonurdf/URDF/rover_sim/install/setup.bash
ros2 run rover_sim ps4_drive_node.py
```

### PS4 Kontrolcü Kullanımı

1. **X butonunu basılı tut** (güvenlik kilidi)
2. **R2** = İleri git
3. **L2** = Geri git
4. **Sol analog yatay** = Sağa/sola dön

### Faydalı Komutlar

```bash
# Topic'leri listele
ros2 topic list

# Joy mesajlarını izle
ros2 topic echo /joy

# cmd_vel mesajlarını izle
ros2 topic echo /diff_drive_controller/cmd_vel_unstamped

# Controller durumunu kontrol et
ros2 control list_controllers

# Joint state'leri izle
ros2 topic echo /joint_states
```

---

## 📊 Performans Notları

- **Controller update rate:** 50 Hz
- **Gazebo physics:** 1000 Hz (1ms step)
- **Joy autorepeat:** 20 Hz
- **Watchdog timeout:** 0.5s (komut gelmezse robot durur)

---

## 🔧 Sorun Giderme Kontrol Listesi

1. [ ] PS4 kontrolcü bağlı mı? (`ls /dev/input/js*`)
2. [ ] Doğru joystick cihazı mı? (`cat /sys/class/input/js1/device/name`)
3. [ ] Simülasyon çalışıyor mu? (`ros2 node list`)
4. [ ] Controller'lar aktif mi? (`ros2 control list_controllers`)
5. [ ] Joy mesajları geliyor mu? (`ros2 topic echo /joy --once`)
6. [ ] cmd_vel yayınlanıyor mu? (`ros2 topic echo /diff_drive_controller/cmd_vel_unstamped --once`)
7. [ ] Gazebo Play butonuna basıldı mı?

---

## 📝 Versiyon Geçmişi

| Tarih | Değişiklik |
|-------|------------|
| 2026-01-23 | İlk URDF oluşturuldu |
| 2026-01-24 | ros2_control entegrasyonu |
| 2026-01-25 | PS4 kontrolcü desteği |
| 2026-01-25 | Mesh path düzeltmeleri |
| 2026-01-25 | Tekerlek eksen düzeltmeleri |
| 2026-01-25 | Deadzone optimizasyonu |

---

## 👥 Katkıda Bulunanlar

- Proje Sahibi: Ali
- ROS 2 / Gazebo Entegrasyonu: GitHub Copilot

---

## 📄 Lisans

Apache 2.0 License
