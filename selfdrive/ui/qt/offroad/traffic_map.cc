#include "selfdrive/ui/qt/offroad/traffic_map.h"

#include <QDebug>
#include <QHBoxLayout>
#include <QPainter>
#include <QPainterPath>
#include <QStyle>
#include <QDesktopServices>
#include <QUrl>

#include "selfdrive/ui/ui.h"

TrafficMapButton::TrafficMapButton(QWidget *parent) : QPushButton(parent) {
  // go to toggles and expand experimental mode description
  connect(this, &QPushButton::clicked, [=]() {
      QDesktopServices::openUrl(QUrl("https://fdot.maps.arcgis.com/apps/dashboards/d51a932d281b4832b5e06c1700b42493"));
   });

  setFixedHeight(125);
  QHBoxLayout *main_layout = new QHBoxLayout;
  main_layout->setContentsMargins(horizontal_padding, 0, horizontal_padding, 0);

  mode_label = new QLabel;
  mode_icon = new QLabel;
  mode_icon->setSizePolicy(QSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed));

  main_layout->addWidget(mode_label, 1, Qt::AlignLeft);
  main_layout->addWidget(mode_icon, 0, Qt::AlignRight);

  setLayout(main_layout);

  setStyleSheet(R"(
    QPushButton {
      border: none;
    }

    QLabel {
      font-size: 45px;
      font-weight: 300;
      text-align: left;
      font-family: JetBrainsMono;
      color: #000000;
    }
  )");
}

void TrafficMapButton::paintEvent(QPaintEvent *event) {
  QPainter p(this);
  p.setPen(Qt::NoPen);
  p.setRenderHint(QPainter::Antialiasing);

  QPainterPath path;
  path.addRoundedRect(rect(), 10, 10);

  // gradient
  bool pressed = isDown();
  QLinearGradient gradient(rect().left(), 0, rect().right(), 0);
  gradient.setColorAt(0, QColor(20, 255, 171, pressed ? 0xcc : 0xff));
  gradient.setColorAt(1, QColor(35, 149, 255, pressed ? 0xcc : 0xff));
  p.fillPath(path, gradient);
}

void TrafficMapButton::showEvent(QShowEvent *event) {
  // experimental_mode = params.getBool("ExperimentalMode");
  // mode_icon->setPixmap(experimental_mode ? experimental_pixmap : chill_pixmap);
  mode_label->setText("Launch Traffic Map");
}
