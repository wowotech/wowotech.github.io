---
title: "Linux power supply class(1)_软件架构及API汇整"
date: 2015-03-13T22:14:23+08:00
url: "/pm_subsystem/psy_class_overview.html"
gid: "155"
emlog_type: "blog"
summary: "\r\n\tpower supply class为编写供电设备（power supply，后面简称PSY）的驱动提供了统一的框架，功能包括：\r\n\r\n\r\n\t1）抽象PSY设备的共性，向用户空间提供统一的API。\r\n\r\n\r\n\t2）为底层PSY驱动的编写，提供简单、统一的方式。同时封装并实现公共逻辑，驱动工程师只需把精力集中在和硬件相关的部分即可。\r\n\r\n\r\n\t本文将从设计思路、软件架构、API说明以及怎么编"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "class", "psy"]
views: 50380
comment_count: 43
aliases:
  - "/pm_subsystem/155.html"
  - "/155.html"
---

#### 1. 前言

power supply class为编写供电设备（power supply，后面简称PSY）的驱动提供了统一的框架，功能包括：

1）抽象PSY设备的共性，向用户空间提供统一的API。

2）为底层PSY驱动的编写，提供简单、统一的方式。同时封装并实现公共逻辑，驱动工程师只需把精力集中在和硬件相关的部分即可。

本文将从设计思路、软件架构、API说明以及怎么编写power supply driver四个角度，介绍power supply class。并会在下一篇文章中，分析power supply class的内部逻辑。如果有时间，会在第三篇文章中，以android系统为例，介绍应用软件怎样利用power supply class，监控系统的供电状态。

注：其实所有的class（如input subsystem），思路都是这样的----抽象共性、统一接口、屏蔽细节。我们在“[Linux设备模型(7)\_*Class*](/device_model/class.html)”中介绍过，本文在介绍power supply class同时，也以此为例，进一步理解设备模型中class的存在意义和使用方法。

#### 2. 设计思路

先来回答一个问题：kernel中设备驱动的目的，是管理设备，并提供给用户空间程序使用，那么对PSY设备而言，kernel要管理什么？用户空间程序要使用什么？

其实PSY设备是一个特例，它的目的很单纯，就是为系统供电。如果只考虑这个目的，就不需要任何驱动了，但情况会稍微复杂，因为：

1）PSY设备可能是电池设备（battery，这在嵌入式系统中很常见），这会引申出电量检测、充电管理等多个议题。

> 此时，PSY driver需要管理的事情包括：检测电池类型；检测电池电量；检测充电状态；等等。而用户空间程序则需要将检测到的结果，显示给用户。

2）系统中可能有多个PSY设备，这些设备还可能有级联关系，如有些平板电脑中，可能同时存在DC-charger、USB-charger和battery三个供电设备，其中DC-charger和USB-charger可能会给battery供电，再由battery向系统供电。

> 此时，PSY driver需要管理的事情包括：获取外部供电设备的连接状态；充电状态；等等。同样，用户空间程序需要将这些信息显示给用户。

那么，共性已经总结出来了：PSY driver的主要功能，就是向用户空间程序汇整各类状态信息。因此，power supply class的核心思路就是：

> 将这些状态信息，抽象为“属性（properties）”。由于状态信息的类型是有限的，properties的个数也是有限的。
>
> PSY driver只需要负责：该PSY设备具有哪些“属性”；这些“属性”的“值（value）”是什么；当“属性值”发生改变时，通知power supply class。
>
> power supply class负责：将某个PSY设备支持的属性及其value，以sysfs的形式，提供给用户空间；当属性值改变时，以uevent的形式，广播给用户空间程序。
>
> 另外，power supply class也会协助处理PSY级联的情况（后面会详细描述）。

#### 3. 软件架构和API汇整

**3.1 软件架构**

power supply class位于drivers/power/目录中，主要由3部分组成（可参考下图的软件架构）：

1）power supply core，用于抽象核心数据结构、实现公共逻辑。位于drivers/power/power\_supply\_core.c中。

2）power supply sysfs，实现sysfs以及uevent功能。位于drivers/power/power\_supply\_sysfs.c中。

3）power supply leds，基于linux led class，提供PSY设备状态指示的通用实现。位于drivers/power/power\_suppply\_leds.c中。

最后，驱动工程师可以基于power supply class，实现具体的PSY drivers，主要处理平台相关、硬件相关的逻辑。这些drivers都位于drivers/power/目录下。

[![power supply class](/content/uploadfile/201503/ae4b4b29f4ab14f43f0b7869b43697cd20150313141413.gif "power supply class")](/content/uploadfile/201503/143a22f04dd02aa9d5864c416c2574d320150313141413.gif)

**3.2 核心数据结构**

1）struct power\_supply

struct power\_supply为power supply class的核心数据结构，用于抽象PSY设备。其定义如下：

```
   1: /* include/linux/power_supply.h */
```

```
   2: struct power_supply {
```

```
   3:     const char *name;
```

```
   4:     enum power_supply_type type;
```

```
   5:     enum power_supply_property *properties;
```

```
   6:     size_t num_properties;
```

```
   7:  
```

```
   8:     char **supplied_to;
```

```
   9:     size_t num_supplicants;
```

```
  10:  
```

```
  11:     char **supplied_from;
```

```
  12:     size_t num_supplies;
```

```
  13:     struct device_node *of_node;
```

```
  14:  
```

```
  15:     int (*get_property)(struct power_supply *psy,
```

```
  16:                 enum power_supply_property psp,
```

```
  17:                 union power_supply_propval *val);
```

```
  18:     int (*set_property)(struct power_supply *psy,
```

```
  19:                 enum power_supply_property psp,
```

```
  20:                 const union power_supply_propval *val);
```

```
  21:     int (*property_is_writeable)(struct power_supply *psy,
```

```
  22:                      enum power_supply_property psp);
```

```
  23:     void (*external_power_changed)(struct power_supply *psy);
```

```
  24:     void (*set_charged)(struct power_supply *psy);
```

```
  25:  
```

```
  26:     /* For APM emulation, think legacy userspace. */
```

```
  27:     int use_for_apm;
```

```
  28:  
```

```
  29:     /* private */
```

```
  30:     struct device *dev;
```

```
  31:     struct work_struct changed_work;
```

```
  32:     spinlock_t changed_lock;
```

```
  33:     bool changed;
```

```
  34: #ifdef CONFIG_THERMAL
```

```
  35:     struct thermal_zone_device *tzd;
```

```
  36:     struct thermal_cooling_device *tcd;
```

```
  37: #endif
```

```
  38:  
```

```
  39: #ifdef CONFIG_LEDS_TRIGGERS
```

```
  40:     struct led_trigger *charging_full_trig;
```

```
  41:     char *charging_full_trig_name;
```

```
  42:     struct led_trigger *charging_trig;
```

```
  43:     char *charging_trig_name;
```

```
  44:     struct led_trigger *full_trig;
```

```
  45:     char *full_trig_name;
```

```
  46:     struct led_trigger *online_trig;
```

```
  47:     char *online_trig_name;
```

```
  48:     struct led_trigger *charging_blink_full_solid_trig;
```

```
  49:     char *charging_blink_full_solid_trig_name;
```

```
  50: #endif
```

```
  51: };
```

> name，该PSY的名称；
>
> type，该PSY的类型，枚举型，包括：battery、USB charger等等（后面会详细介绍）；
>
> properties，该PSY具有的属性列表，枚举型（后面会详细介绍）；
>   
> num\_properties，属性的个数；
>
> supplied\_to，一个字符串数组，保存了由该PSY供电的PSY列表，以此可将PSY组织成相互级联的PSY链。这些“被供电”的PSY，称作supplicant（客户端、乞求者）；
>   
> num\_supplicants， supplicant的个数；
>
> supplied\_from，一个字符串数组，保存了向该PSY供电的PSY列表，也称作supply（提供者）。从另一个方向，组织PSY之间的级联关系；
>   
> num\_supplies，supply的个数；
>
> get\_property/set\_property，PSY driver需要重点实现的两个回调函数，用于获取/设置属性值；
>
> property\_is\_writeable，返回指定的属性值是否可写（用于sysfs）；
>
> external\_power\_changed，当一个PSY设备存在supply PSY，且该supply PSY的属性发生改变（如online、offline）时，power supply core会调用该回调函数，通知PSY driver，以便让它做出相应的处理；
>
> set\_charged，该回调函数的应用场景有点奇怪：外部模块通知PSY driver，该PSY设备的状态改变了。自己改变了自己不知道，要外部通知，希望大家在实际工作中不要遇到，不然太纠结了；
>
> changed\_work/changed\_lock/changed，一个用于处理状态改变的workqueue，主要思路是：当该PSY的状态发生改变，启动一个workqueue，查询并通知所有的supplicants；
>
> tzd/tcd，如果该PSY具有温度等属性，则需要借助linux generic thermal sysfs drivers（温控子系统）的框架，注册相应的thermal设备，后面会详细介绍；
>
> led triggers，如果配置了CONFIG\_LEDS\_TRIGGERS，则调用linux led class的接口，注册相应的LED设备，用于PSY状态指示；
>
> dev/of\_node，用于保存device、of\_node等指针。

2）PSY类型

PSY类型由enum power\_supply\_type定义：

```
   1: enum power_supply_type {
```

```
   2:     POWER_SUPPLY_TYPE_UNKNOWN = 0,
```

```
   3:     POWER_SUPPLY_TYPE_BATTERY,
```

```
   4:     POWER_SUPPLY_TYPE_UPS,
```

```
   5:     POWER_SUPPLY_TYPE_MAINS,
```

```
   6:     POWER_SUPPLY_TYPE_USB,        /* Standard Downstream Port */
```

```
   7:     POWER_SUPPLY_TYPE_USB_DCP,    /* Dedicated Charging Port */
```

```
   8:     POWER_SUPPLY_TYPE_USB_CDP,    /* Charging Downstream Port */
```

```
   9:     POWER_SUPPLY_TYPE_USB_ACA,    /* Accessory Charger Adapters */
```

```
  10: };
```

> POWER\_SUPPLY\_TYPE\_UNKOWN，未知；
>
> POWER\_SUPPLY\_TYPE\_BATTERY，电池，嵌入式设备、手持式智能设备常用的供电形式；
>
> POWER\_SUPPLY\_TYPE\_UPS，Uninterruptible Power System/Uninterruptible Power Supply，不间断式供电设备，通过将交流电和蓄电池连接，正常情况下由交流电供电，同时向蓄电池充电。当交流电断电时，由蓄电池紧急供电。一般用于服务器等设备；
>
> POWER\_SUPPLY\_TYPE\_MAINS，主供电设备，如笔记本电脑的适配器，其特点是可以单独供电，当其断电时，再由辅助供电设备供电（如battery）；
>
> POWER\_SUPPLY\_TYPE\_USB/POWER\_SUPPLY\_TYPE\_USB\_DCP
>   
> /POWER\_SUPPLY\_TYPE\_USB\_CDP/POWER\_SUPPLY\_TYPE\_USB\_ACA，USB类型的供电，不同点在于充电电流的限制，由USB Battery Charge Spec规定，具体可参考USB组织的规范，或者参考这个链接（[http://www.cash.idv.tw/wordpress/?p=8334](http://www.cash.idv.tw/wordpress/?p=8334 "http://www.cash.idv.tw/wordpress/?p=8334")，由于是台湾博客，被和谐了，呵呵呵！感兴趣的同学可以找我要）。

3）PSY属性

power supply class将所有可能PSY属性，以枚举型变量（enum power\_supply\_property ）的形式抽象出来，PSY driver可以根据设备的实际情况，从中选取一些。

```
   1: enum power_supply_property {
```

```
   2:     /* Properties of type `int' */
```

```
   3:     POWER_SUPPLY_PROP_STATUS = 0,
```

```
   4:     POWER_SUPPLY_PROP_CHARGE_TYPE,
```

```
   5:     POWER_SUPPLY_PROP_HEALTH,
```

```
   6:     POWER_SUPPLY_PROP_PRESENT,
```

```
   7:     POWER_SUPPLY_PROP_ONLINE,
```

```
   8:     POWER_SUPPLY_PROP_AUTHENTIC,
```

```
   9:     POWER_SUPPLY_PROP_TECHNOLOGY,
```

```
  10:     POWER_SUPPLY_PROP_CYCLE_COUNT,
```

```
  11:     POWER_SUPPLY_PROP_VOLTAGE_MAX,
```

```
  12:     POWER_SUPPLY_PROP_VOLTAGE_MIN,
```

```
  13:     POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN,
```

```
  14:     POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN,
```

```
  15:     POWER_SUPPLY_PROP_VOLTAGE_NOW,
```

```
  16:     POWER_SUPPLY_PROP_VOLTAGE_AVG,
```

```
  17:     POWER_SUPPLY_PROP_VOLTAGE_OCV,
```

```
  18:     POWER_SUPPLY_PROP_VOLTAGE_BOOT,
```

```
  19:     POWER_SUPPLY_PROP_CURRENT_MAX,
```

```
  20:     POWER_SUPPLY_PROP_CURRENT_NOW,
```

```
  21:     POWER_SUPPLY_PROP_CURRENT_AVG,
```

```
  22:     POWER_SUPPLY_PROP_CURRENT_BOOT,
```

```
  23:     POWER_SUPPLY_PROP_POWER_NOW,
```

```
  24:     POWER_SUPPLY_PROP_POWER_AVG,
```

```
  25:     POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
```

```
  26:     POWER_SUPPLY_PROP_CHARGE_EMPTY_DESIGN,
```

```
  27:     POWER_SUPPLY_PROP_CHARGE_FULL,
```

```
  28:     POWER_SUPPLY_PROP_CHARGE_EMPTY,
```

```
  29:     POWER_SUPPLY_PROP_CHARGE_NOW,
```

```
  30:     POWER_SUPPLY_PROP_CHARGE_AVG,
```

```
  31:     POWER_SUPPLY_PROP_CHARGE_COUNTER,
```

```
  32:     POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT,
```

```
  33:     POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT_MAX,
```

```
  34:     POWER_SUPPLY_PROP_CONSTANT_CHARGE_VOLTAGE,
```

```
  35:     POWER_SUPPLY_PROP_CONSTANT_CHARGE_VOLTAGE_MAX,
```

```
  36:     POWER_SUPPLY_PROP_CHARGE_CONTROL_LIMIT,
```

```
  37:     POWER_SUPPLY_PROP_CHARGE_CONTROL_LIMIT_MAX,
```

```
  38:     POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,
```

```
  39:     POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN,
```

```
  40:     POWER_SUPPLY_PROP_ENERGY_EMPTY_DESIGN,
```

```
  41:     POWER_SUPPLY_PROP_ENERGY_FULL,
```

```
  42:     POWER_SUPPLY_PROP_ENERGY_EMPTY,
```

```
  43:     POWER_SUPPLY_PROP_ENERGY_NOW,
```

```
  44:     POWER_SUPPLY_PROP_ENERGY_AVG,
```

```
  45:     POWER_SUPPLY_PROP_CAPACITY, /* in percents! */
```

```
  46:     POWER_SUPPLY_PROP_CAPACITY_ALERT_MIN, /* in percents! */
```

```
  47:     POWER_SUPPLY_PROP_CAPACITY_ALERT_MAX, /* in percents! */
```

```
  48:     POWER_SUPPLY_PROP_CAPACITY_LEVEL,
```

```
  49:     POWER_SUPPLY_PROP_TEMP,
```

```
  50:     POWER_SUPPLY_PROP_TEMP_MAX,
```

```
  51:     POWER_SUPPLY_PROP_TEMP_MIN,
```

```
  52:     POWER_SUPPLY_PROP_TEMP_ALERT_MIN,
```

```
  53:     POWER_SUPPLY_PROP_TEMP_ALERT_MAX,
```

```
  54:     POWER_SUPPLY_PROP_TEMP_AMBIENT,
```

```
  55:     POWER_SUPPLY_PROP_TEMP_AMBIENT_ALERT_MIN,
```

```
  56:     POWER_SUPPLY_PROP_TEMP_AMBIENT_ALERT_MAX,
```

```
  57:     POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,
```

```
  58:     POWER_SUPPLY_PROP_TIME_TO_EMPTY_AVG,
```

```
  59:     POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
```

```
  60:     POWER_SUPPLY_PROP_TIME_TO_FULL_AVG,
```

```
  61:     POWER_SUPPLY_PROP_TYPE, /* use power_supply.type instead */
```

```
  62:     POWER_SUPPLY_PROP_SCOPE,
```

```
  63:     POWER_SUPPLY_PROP_CHARGE_TERM_CURRENT,
```

```
  64:     POWER_SUPPLY_PROP_CALIBRATE,
```

```
  65:     /* Properties of type `const char *' */
```

```
  66:     POWER_SUPPLY_PROP_MODEL_NAME,
```

```
  67:     POWER_SUPPLY_PROP_MANUFACTURER,
```

```
  68:     POWER_SUPPLY_PROP_SERIAL_NUMBER,
```

```
  69: };
```

> 属性值相当多，考虑到篇幅问题，本文只列举几个（它们也是power supply sysfs支持的属性），其它的大家可以自行理解。
>
> POWER\_SUPPLY\_PROP\_STATUS，该PSY的status，主要是充电状态，包括："Unknown", "Charging", "Discharging", "Not charging", "Full"，由枚举型变量（POWER\_SUPPLY\_STATUS\_\*）定义。根据设计方案的不同，充电类型的PSY，或者battery类型的PSY，都可能具备该属性；
>
> POWER\_SUPPLY\_PROP\_CHARGE\_TYPE，充电类型，包括："Unknown", "N/A", "Trickle", "Fast"，由枚举型变量（POWER\_SUPPLY\_CHARGE\_TYPE\_\*）定义；同理根据设计方案的不同，充电类型的PSY，或者battery类型的PSY，都可能具备该属性；
>
> POWER\_SUPPLY\_PROP\_HEALTH，“健康”情况，包括："Unknown", "Good", "Overheat", "Dead", "Over voltage"等等, 由枚举型变量（POWER\_SUPPLY\_HEALTH\_\*）定义。一般用于battery类型的PSY；
>
> POWER\_SUPPLY\_PROP\_TECHNOLOGY，采用的技术，包括："Unknown", "NiMH", "Li-ion", "Li-poly", "LiFe", "NiCd", "LiMn"，由枚举型变量（POWER\_SUPPLY\_TECHNOLOGY\_\*）定义。一般用于battery类型的PSY；
>
> POWER\_SUPPLY\_PROP\_CAPACITY\_LEVEL，容量，包括："Unknown", "Critical", "Low", "Normal", "High", "Full"，由枚举型变量（POWER\_SUPPLY\_CAPACITY\_LEVEL\_\*）定义。一般用于battery类型的PSY；
>
> POWER\_SUPPLY\_PROP\_TYPE，PSY类型，比较特殊，保存在“psy->type”变量中，而不在properties数组中。

**3.3 向具体的PSY driver提供的API**

power supply class首要任务，是向PSY driver提供统一的驱动编写接口，主要包括：

1）PSY的register/unregister API

```
   1: extern int power_supply_register(struct device *parent, 
```

```
   2:                                  struct power_supply *psy); 
```

```
   3: extern int power_supply_register_no_ws(struct device *parent, 
```

```
   4:                                  struct power_supply *psy); 
```

```
   5: extern void power_supply_unregister(struct power_supply *psy);
```

> 其中power\_supply\_register和power\_supply\_register\_no\_ws的区别是：power\_supply\_register注册的PSY，具备wakeup系统的能力，而power\_supply\_register\_no\_ws不具备。

2）PSY状态改变时通知power supply core的API

```
   1: extern void power_supply_changed(struct power_supply *psy);
```

> 当PSY driver检测到该设备某些属性值改变时，需要调用这个接口，通知power supply core，power supply core会有如下动作：
>
> 如果该PSY是其它PSY的供电源，调用这些PSY的external\_power\_changed回调函数，通知它们（这些PSY具体要做些什么，由它们的自身逻辑决定）；
>
> 如果配置了CONFIG\_LEDS\_TRIGGERS，调用power\_supply\_update\_leds，更新该PSY有关的led状态；
>
> 发送notifier，通知那些关心PSY设备状态的drivers；
>
> 以统一的格式，向用户空间发送uevent（这就是设备模型中class的魅力，对外接口由class core提供，可以节省driver的工作量，同时确保了接口的一致性）。

3）其它杂项接口

```
   1: extern struct power_supply *power_supply_get_by_name(const char *name); 
```

```
   2: extern struct power_supply *power_supply_get_by_phandle(struct device_node *np, 
```

```
   3:                                                         const char *property); 
```

```
   4: extern int power_supply_am_i_supplied(struct power_supply *psy); 
```

```
   5: extern int power_supply_set_battery_charged(struct power_supply *psy); 
```

```
   6: extern int power_supply_is_system_supplied(void); 
```

```
   7: extern int power_supply_powers(struct power_supply *psy, struct device *dev);
```

> power\_supply\_get\_by\_name，通过名字获取PSY指针。
>
> power\_supply\_get\_by\_phandle，从DTS中，解析出对应dePSY指针（后面会详细介绍）。
>
> power\_supply\_am\_i\_supplied，查询自己是否由其它PSY供电。
>
> power\_supply\_set\_battery\_charged，调用指定PSY的set\_charged回调。
>
> power\_supply\_is\_system\_supplied，查询系统是否有有效的或者处于online状态的PSY，如果没有，可能为桌面系统。
>
> power\_supply\_powers，在指定设备（通常是该PSY设备）的sysfs目录（/sys/devices/xxx/）下，创建指定PSY的符号链接（/sys/devices/xxx/powers）。

**3.4 向其它driver提供的用于接收PSY状态改变notifier的API**

```
   1: extern int power_supply_reg_notifier(struct notifier_block *nb); 
```

```
   2: extern void power_supply_unreg_notifier(struct notifier_block *nb);
```

> 通过notifier注册接口注册notifier之后，系统任何PSY设备的状态发生改变，并调用了power\_supply\_changed接口，power supply core就是通知notifier的监听者。

#### 3.5 向用户空间程序提供的API

power supply class通过两种形式向用户空间提供接口。

1）uevent（具体可参考“[Linux设备模型(3)\_*Uevent*](/device_model/uevent.html)”），以“名字=value”的形式，上报所有property的值，格式如下：

> POWER\_SUPPLY\_NAME=xxx /\* power supply name \*/
>   
> POWER\_SUPPLY\_xxx1=xxx /\* property = value \*/
>   
> POWER\_SUPPLY\_xxx2=xxx
>   
> …

uevent一般会在PSY设备添加到kernel时，或者PSY属性发生改变时（可参考3.3中的介绍）发送。

2）sysfs

power supply class在power\_supply\_sysfs.c中，定义了相当多的默认attribute（见下面），如果某个PSY设备具有某个属性，该属性对应的attribute就会体现在sysfs中（一般位于“/sys/class/power\_supply/xxx/”中）。

```
   1: /* Must be in the same order as POWER_SUPPLY_PROP_* */
```

```
   2: static struct device_attribute power_supply_attrs[] = {
```

```
   3:     /* Properties of type `int' */
```

```
   4:     POWER_SUPPLY_ATTR(status),
```

```
   5:     POWER_SUPPLY_ATTR(charge_type),
```

```
   6:     POWER_SUPPLY_ATTR(health),
```

```
   7:     POWER_SUPPLY_ATTR(present),
```

```
   8:     POWER_SUPPLY_ATTR(online),
```

```
   9:     POWER_SUPPLY_ATTR(authentic),
```

```
  10:     POWER_SUPPLY_ATTR(technology),
```

```
  11:     POWER_SUPPLY_ATTR(cycle_count),
```

```
  12:     POWER_SUPPLY_ATTR(voltage_max),
```

```
  13:     POWER_SUPPLY_ATTR(voltage_min),
```

```
  14:     POWER_SUPPLY_ATTR(voltage_max_design),
```

```
  15:     POWER_SUPPLY_ATTR(voltage_min_design),
```

```
  16:     POWER_SUPPLY_ATTR(voltage_now),
```

```
  17:     POWER_SUPPLY_ATTR(voltage_avg),
```

```
  18:     POWER_SUPPLY_ATTR(voltage_ocv),
```

```
  19:     POWER_SUPPLY_ATTR(voltage_boot),
```

```
  20:     POWER_SUPPLY_ATTR(current_max),
```

```
  21:     POWER_SUPPLY_ATTR(current_now),
```

```
  22:     POWER_SUPPLY_ATTR(current_avg),
```

```
  23:     POWER_SUPPLY_ATTR(current_boot),
```

```
  24:     POWER_SUPPLY_ATTR(power_now),
```

```
  25:     POWER_SUPPLY_ATTR(power_avg),
```

```
  26:     POWER_SUPPLY_ATTR(charge_full_design),
```

```
  27:     POWER_SUPPLY_ATTR(charge_empty_design),
```

```
  28:     POWER_SUPPLY_ATTR(charge_full),
```

```
  29:     POWER_SUPPLY_ATTR(charge_empty),
```

```
  30:     POWER_SUPPLY_ATTR(charge_now),
```

```
  31:     POWER_SUPPLY_ATTR(charge_avg),
```

```
  32:     POWER_SUPPLY_ATTR(charge_counter),
```

```
  33:     POWER_SUPPLY_ATTR(constant_charge_current),
```

```
  34:     POWER_SUPPLY_ATTR(constant_charge_current_max),
```

```
  35:     POWER_SUPPLY_ATTR(constant_charge_voltage),
```

```
  36:     POWER_SUPPLY_ATTR(constant_charge_voltage_max),
```

```
  37:     POWER_SUPPLY_ATTR(charge_control_limit),
```

```
  38:     POWER_SUPPLY_ATTR(charge_control_limit_max),
```

```
  39:     POWER_SUPPLY_ATTR(input_current_limit),
```

```
  40:     POWER_SUPPLY_ATTR(energy_full_design),
```

```
  41:     POWER_SUPPLY_ATTR(energy_empty_design),
```

```
  42:     POWER_SUPPLY_ATTR(energy_full),
```

```
  43:     POWER_SUPPLY_ATTR(energy_empty),
```

```
  44:     POWER_SUPPLY_ATTR(energy_now),
```

```
  45:     POWER_SUPPLY_ATTR(energy_avg),
```

```
  46:     POWER_SUPPLY_ATTR(capacity),
```

```
  47:     POWER_SUPPLY_ATTR(capacity_alert_min),
```

```
  48:     POWER_SUPPLY_ATTR(capacity_alert_max),
```

```
  49:     POWER_SUPPLY_ATTR(capacity_level),
```

```
  50:     POWER_SUPPLY_ATTR(temp),
```

```
  51:     POWER_SUPPLY_ATTR(temp_max),
```

```
  52:     POWER_SUPPLY_ATTR(temp_min),
```

```
  53:     POWER_SUPPLY_ATTR(temp_alert_min),
```

```
  54:     POWER_SUPPLY_ATTR(temp_alert_max),
```

```
  55:     POWER_SUPPLY_ATTR(temp_ambient),
```

```
  56:     POWER_SUPPLY_ATTR(temp_ambient_alert_min),
```

```
  57:     POWER_SUPPLY_ATTR(temp_ambient_alert_max),
```

```
  58:     POWER_SUPPLY_ATTR(time_to_empty_now),
```

```
  59:     POWER_SUPPLY_ATTR(time_to_empty_avg),
```

```
  60:     POWER_SUPPLY_ATTR(time_to_full_now),
```

```
  61:     POWER_SUPPLY_ATTR(time_to_full_avg),
```

```
  62:     POWER_SUPPLY_ATTR(type),
```

```
  63:     POWER_SUPPLY_ATTR(scope),
```

```
  64:     POWER_SUPPLY_ATTR(charge_term_current),
```

```
  65:     POWER_SUPPLY_ATTR(calibrate),
```

```
  66:     /* Properties of type `const char *' */
```

```
  67:     POWER_SUPPLY_ATTR(model_name),
```

```
  68:     POWER_SUPPLY_ATTR(manufacturer),
```

```
  69:     POWER_SUPPLY_ATTR(serial_number),
```

```
  70: };
```

具体意义这里就不再详细说明了。

#### 4. 怎样基于power supply class编写PSY driver

最后从PSY driver的角度，说明一下怎么基于power supply class，编写驱动：

1）根据硬件spec，确定该PSY设备具备哪些特性，并把它们和enum power\_supply\_property 中所定义的property对应。

2）根据实际情况，实现这些properties的get/set接口。

3）定义一个struct power\_supply变量，并初始化必要的字段后，调用power\_supply\_register或者power\_supply\_register\_no\_ws，将其注册到kernel中。

4）根据实际情况，启动设备属性变化的监控逻辑，例如中断、轮询等，并在发生改变时，调用power\_supply\_changed，通知power supply core。

也许您会笑，说着简单啊！确实如此，不变的原则：framework只能给我们提供良好的机制、便捷的方式、等等，但是，设备要做什么事情，只有设备驱动最清楚，永远都不可能偷懒啊！

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/psy_class_overview.html)。
