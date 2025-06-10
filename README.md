# hacs-chinese-holidays
HACS Chinese holidays

## 安装

### [HACS](https://hacs.xyz/)

一键安装自HACS:

[![Open your Home Assistant instance and open the Xiaomi Home integration inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jamebal&repository=hacs-chinese-holidays&category=integration)


## 配置

在configuration.yaml文件里, 重启生效.

```yaml
sensor:
  - platform: holiday_status
```