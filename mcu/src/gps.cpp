#include "gps.h"

GpsFix NullGpsProvider::currentFix() const {
  return GpsFix{};
}
