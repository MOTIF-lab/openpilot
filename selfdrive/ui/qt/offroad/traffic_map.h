#pragma once

#include <QLabel>
#include <QPushButton>

#include "common/params.h"

class TrafficMapButton : public QPushButton {
  Q_OBJECT

public:
  explicit TrafficMapButton(QWidget* parent = 0);

signals:
  void openMap();

private:
  void showEvent(QShowEvent *event) override;

  Params params;
  int img_width = 100;
  int horizontal_padding = 30;
  QLabel *mode_label;
  QLabel *mode_icon;

protected:
  void paintEvent(QPaintEvent *event) override;
};
