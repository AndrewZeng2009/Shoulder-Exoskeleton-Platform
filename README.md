# Shoulder Exoskeleton Platform
An open-source, low-cost (~$300) cable-driven shoulder exoskeleton designed as an accessible research and prototyping platform. Most existing shoulder exoskeleton platforms are expensive, proprietary, and inaccessible to small research groups, students, and independent developers. This platform addresses that gap by integrating established actuation and sensing technologies into a reproducible, modifiable system that can be fabricated with off-the-shelf components and a standard 3D printer.

The system combines a servo-driven Bowden cable transmission with passive bungee elastic assistance and a tri-modal sensor suite — surface EMG, IMU, and load cell — controlled through an Arduino Uno. An IR remote switches between off, sensor-only, and active assistance modes, with an adjustable EMG activation threshold. Experimental validation demonstrated 22–42% reduction in deltoid muscle activation under active assistance across a range of loads and motions.

The target audience is the open-source community: students, hobbyists, and small labs who want to experiment with exoskeleton hardware, sensing modalities, and control algorithms without a large resource investment.

---

## Repository Structure

**CAD/**
- `native/` — Fusion 360 source files (.f3z)
- `step/` — Universal CAD files (.step)
- `stl/` — 3D-printable components (.stl)

**Electronics/**
- `Simple Schematic.png` — Full wiring diagram

**Firmware/**
- `Shoulder_Exoskeleton_System_Code.ino` — Arduino control firmware
- `State Machine Diagram.png` — Control state machine diagram

**Summary Data/**
- `EMG Data.pdf` — Processed EMG results across all assistance conditions, loads, and motions
- `IMU Data.pdf` — Processed range-of-motion (Euler angle) data
- `Torque Data.pdf` — Processed bench and in-vivo torque results

**Docs/**
- `BOM.md` — Bill of materials with sourcing and pricing
- `Assembly_Guide.pdf` — Step-by-step build instructions

---

## Getting Started
1. Print all STL components and source hardware per `Docs/BOM.md`
2. Assemble the platform following `Docs/Assembly_Guide.pdf`
3. Wire electronics per `Electronics/Simple Schematic.png`
4. Upload `Firmware/Shoulder_Exoskeleton_System_Code.ino` to an Arduino Uno
5. Open Serial Monitor at 115200 baud to verify all sensors

---

## Contact
Andrew Zeng — andrew10n06@gmail.com
