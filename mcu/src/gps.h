#pragma once

struct GpsFix {
  bool available = false;
  float speed_mps = 0.0f;
  double latitude = 0.0;
  double longitude = 0.0;
};

class GpsProvider {
 public:
  virtual ~GpsProvider() = default;
  virtual GpsFix currentFix() const = 0;
};

class NullGpsProvider final : public GpsProvider {
 public:
  GpsFix currentFix() const override;
};
