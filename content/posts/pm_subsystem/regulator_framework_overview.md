---
title: "Linux Regulator Framework(1)_概述"
date: 2015-03-20T21:42:00+08:00
url: "/pm_subsystem/regulator_framework_overview.html"
gid: "156"
emlog_type: "blog"
summary: "Regulator，中文名翻译为“稳定器”，在电子工程中，是voltage regulator（稳压器）或者current regulator（稳流器）的简称，指可以自动维持恒定电压（或电流）的装置。 voltage regulator最早应用于功放电路中，主要用于滤除电源纹波（100或者120Hz）和噪声，以及避免“输出电压随负载的变化而变化”的情况。后来，随着IC级别的regulator的出现"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "regulator", "软件架构"]
views: 48256
comment_count: 18
aliases:
  - "/pm_subsystem/156.html"
  - "/156.html"
---

#### 1. 前言

Regulator，中文名翻译为“稳定器”，在电子工程中，是voltage regulator（稳压器）或者current regulator（稳流器）的简称，指可以自动维持恒定电压（或电流）的装置。

voltage regulator最早应用于功放电路中，主要用于滤除电源纹波（100或者120Hz）和噪声，以及避免“输出电压随负载的变化而变化”的情况。后来，随着IC级别的regulator的出现（便宜了），voltage regulator几乎存在于任何的电子设备中。例如我们常见的嵌入式设备中，基本上每一种电压，都是经过regulator输出的。

相比较voltage regulator的广泛使用，很少见到current regulator的应用场景（相信大多数的嵌入式工程师都没有接触过）。它一般存在于电流源中，除此之外，它广泛存在于近年来新兴的LED照明设备中。current regulator在LED设备中的作用主要有两个：避免驱动电流超出最大额定值，影响其可靠性；获得预期的亮度要求，并保证各个LED亮度、色度的一致性。

虽然原理比较复杂，但从设备驱动的角度看，regulator的控制应该很简单，就是输出的enable/disable、输出电压或电流的大小的控制。那么，linux kernel的regulator framework到底要做什么呢？这就是本文的目的：弄清楚regulator framework背后思考，并总结出其软件架构（和[common clock framework](/pm_subsystem/clk_overview.html)类似，consumer/provider/core）。

注1：有关regulator的描述，参考自“[http://sound.westhost.com/articles/vi-regulators.html](http://sound.westhost.com/articles/vi-regulators.html "http://sound.westhost.com/articles/vi-regulators.html")”。

注2：kernel中有关regulator framework的介绍写的相当好（Documentation\power\regulator\\*），因此本文大部分内容会参考这些文件。

#### 2. 背后的思考

Linux regulator framework的目的很直接：提供标准的内核接口，控制系统的voltage/current regulators，并提供相应的机制，在系统运行的过程中，动态改变regulators的输出，以达到省电的目的。

看似简单的背后，有些因素不得不考虑。

1）最重要的，就是安全性：

> 在一个系统中，错误的regulator配置是非常危险的，严重时可以损毁硬件。而无论是regulator的使用者（consumer），还是regulator提供者（provider，即regulator driver），都不一定有足够的知识和能力，避免危险发生。因此必须从machine的角度，小心的设计regulator的输出限值（这一般由产品设计、硬件设计决定的）。
>
> 同时，一旦设计确定下来之后，这些限制必须保存在一些相对固定的地方，不能轻易地被软件修改。
>
> 最后，所有的regulator操作，必须是小心的、在可允许范围内的。

2）系统中大部分的设备，都没有动态更改regulator配置的需求，甚至连enable/disable都懒得关心的，framework需要考虑这种情况，尽量简化接口。

3）会存在同一个regulator向多个设备提供power的情况，如果这些设备的需求不同怎么办？

4）regulator之间是否可以级联？如果可以，怎么处理？

这些思考最终都会反映到软件设计上，具体可参考如下的软件架构。

#### 3. 软件架构

基于上面的思考，regulator framework的软件架构如下：

[![regulator framework](/content/uploadfile/201503/57891dad88eeddc1a49785f2b74ce81020150320134157.gif "regulator framework")](/content/uploadfile/201503/b3b17117698259d139aa7aa5e034d6fc20150320134156.gif)

除了machine之外，基本上和[common clock framework](/pm_subsystem/clk_overview.html)的consumer/provider框架类似。

**3.1 machine**

machine的主要功能，是使用软件语言（struct regulator\_init\_data），静态的描述regulator在板级的物理现状，包括：

1）前级regulator（即该regulator的输出是另一个regulator的输入，简称supply regulator）和后级regulator（即该regulator的输入是其它regulator的输出，简称consumer regulator）。

> 这主要用于描述regulator在板级的级联关系，需要留意的是，它和clock不同，这种级联关系是非常确定的，以至于需要使用静态的方式描述，而不是像clock那样，在注册的时候动态指定并形成。

2）该regulator的物理限制（struct regulation\_constraints），包括：

> 输出电压的最大值和最小值（voltage regulator）；   
> 输出电流的最大值和最小值（current regulator）；   
> 允许的操作（修改电压值、修改电流限制、enable、disable等等）；   
> 输入电压是多少（当输入是另一个regulator时）；   
> 是否不允许关闭（always\_on）；   
> 是否启动时就要打开（always\_on）；   
> 等等。

这些限制关系到系统安全，因此必须小心配置。配置完成后，在系统运行的整个过程中，它们都不会再改变了。

**3.2 driver**

driver模块的功能，是从regulator driver的角度，抽象regulator设备。

1）使用struct regulator\_desc描述regulator的静态信息，包括：名字、supply regulator的名字、中断号、操作函数集（struct regulator\_ops）、使用regmap时相应的寄存器即bitmap等等。

2）使用struct regulator\_config，描述regulator的动态信息（所谓的动态信息，体现在struct regulator\_config变量都是局部变量，因此不会永久保存），包括struct regulator\_init\_data指针、设备指针、enable gpio等等。

3）提供regulator的注册接口（regulator\_register/devm\_regulator\_register），该接口接受描述该regulator的两个变量的指针：struct regulator\_desc和struct regulator\_config，并分配一个新的数据结构（struct regulator\_dev，从设备的角度描述regulator），并把静态指针（struct regulator\_desc）和动态指针（struct regulator\_config）提供的信息保存在其中。

4）最后，regulator driver将以为struct regulator\_dev指针为对象，对regulator进行后续的操作。

**3.3 consumer**

consumer的功能，是从regulator consumer的角度，抽象regulator设备（struct regulator），并提供regulator操作相关的接口。包括：

**3.4 core**

core负责上述逻辑的具体实现，并以sysfs的形式，向用户空间提供接口。

#### 4. 接口汇整

本节对regulator framework向各个层次提供的API做一个汇整，具体细节会在后续的文章中详细描述。

**4.1 consumer模块向内核空间consumer提供的接口**

regulator framework向内核空间consumer提供的接口位于“include/linux/regulator/consumer.h”中，包括regulator的获取、使能、修改等接口，如下。

1）struct regulator

struct regulator结构用于从consumer的角度抽象一个regulator，consumer不需要关心该结构的细节，当作一个句柄使用即可（类似struct clk）。

2）regulator的get/put接口

```
   1: struct regulator *__must_check regulator_get(struct device *dev,
```

```
   2:                                              const char *id);
```

```
   3: struct regulator *__must_check devm_regulator_get(struct device *dev,
```

```
   4:                                              const char *id);
```

```
   5: struct regulator *__must_check regulator_get_exclusive(struct device *dev,
```

```
   6:                                                        const char *id);
```

```
   7: struct regulator *__must_check devm_regulator_get_exclusive(struct device *dev,
```

```
   8:                                                         const char *id);
```

```
   9: struct regulator *__must_check regulator_get_optional(struct device *dev,
```

```
  10:                                                       const char *id);
```

```
  11: struct regulator *__must_check devm_regulator_get_optional(struct device *dev,
```

```
  12:                                                            const char *id);
```

```
  13: void regulator_put(struct regulator *regulator);
```

```
  14: void devm_regulator_put(struct regulator *regulator);
```

> 根据是否独占regulator、是否可以多次get，regulator get接口分为三类：
>
> 正常的get，非独占、可以重复get，regulator\_get/devm\_regulator\_get；
>
> 独占性质的get，独占、不可重复get，regulator\_get\_exclusive/devm\_regulator\_get\_exclusive；
>
> optional的get，非独占、不可重复get，regulator\_get\_optional/devm\_regulator\_get\_optional。
>
> get接口的参数为id，会在下一篇文章中详细介绍。

3）supply alias相关的接口

```
   1: int regulator_register_supply_alias(struct device *dev, const char *id,
```

```
   2:                                     struct device *alias_dev,
```

```
   3:                                     const char *alias_id);
```

```
   4: void regulator_unregister_supply_alias(struct device *dev, const char *id);
```

```
   5:  
```

```
   6: int devm_regulator_register_supply_alias(struct device *dev, const char *id,
```

```
   7:                                          struct device *alias_dev,
```

```
   8:                                          const char *alias_id);
```

```
   9: void devm_regulator_unregister_supply_alias(struct device *dev,
```

```
  10:                                             const char *id);
```

```
  11:  
```

```
  12: int devm_regulator_bulk_register_supply_alias(struct device *dev,
```

```
  13:                                               const char *const *id,
```

```
  14:                                               struct device *alias_dev,
```

```
  15:                                               const char *const *alias_id,
```

```
  16:                                               int num_id);
```

```
  17: void devm_regulator_bulk_unregister_supply_alias(struct device *dev,
```

```
  18:                                                  const char *const *id,
```

```
  19:                                                  int num_id);
```

> 具体意义请参考下一篇文章。

4）regulator的控制、状态获取接口

```
   1: int __must_check regulator_enable(struct regulator *regulator);
```

```
   2: int regulator_disable(struct regulator *regulator);
```

```
   3: int regulator_force_disable(struct regulator *regulator);
```

```
   4: int regulator_is_enabled(struct regulator *regulator);
```

```
   5: int regulator_disable_deferred(struct regulator *regulator, int ms);
```

```
   6:  
```

```
   7: int regulator_can_change_voltage(struct regulator *regulator);
```

```
   8: int regulator_count_voltages(struct regulator *regulator);
```

```
   9: int regulator_list_voltage(struct regulator *regulator, unsigned selector);
```

```
  10: int regulator_is_supported_voltage(struct regulator *regulator,
```

```
  11:                                    int min_uV, int max_uV);
```

```
  12: unsigned int regulator_get_linear_step(struct regulator *regulator);
```

```
  13: int regulator_set_voltage(struct regulator *regulator, int min_uV, int max_uV);
```

```
  14: int regulator_set_voltage_time(struct regulator *regulator,
```

```
  15:                                int old_uV, int new_uV);
```

```
  16: int regulator_get_voltage(struct regulator *regulator);
```

```
  17: int regulator_sync_voltage(struct regulator *regulator);
```

```
  18: int regulator_set_current_limit(struct regulator *regulator,
```

```
  19:                                int min_uA, int max_uA);
```

```
  20: int regulator_get_current_limit(struct regulator *regulator);
```

```
  21:  
```

```
  22: int regulator_set_mode(struct regulator *regulator, unsigned int mode);
```

```
  23: unsigned int regulator_get_mode(struct regulator *regulator);
```

```
  24: int regulator_set_optimum_mode(struct regulator *regulator, int load_uA);
```

```
  25:  
```

```
  26: int regulator_allow_bypass(struct regulator *regulator, bool allow);
```

```
  27:  
```

```
  28: struct regmap *regulator_get_regmap(struct regulator *regulator);
```

```
  29: int regulator_get_hardware_vsel_register(struct regulator *regulator,
```

```
  30:                                          unsigned *vsel_reg,
```

```
  31:                                          unsigned *vsel_mask);
```

```
  32: int regulator_list_hardware_vsel(struct regulator *regulator,
```

```
  33:                                  unsigned selector);
```

```
  34:  
```

> 控制有关的包括enable、disable、电压设置、电流设置、mode设置等，其中disable又包括normal、强制、退出等类型。
>
> 状态获取包括：是否enable；是否可以改变电压；支持的电压列表；是否支持指定范围的电压；当前输出电压；当前电流限制；当前mode；等等。
>
> 更为详细的描述，请参考下一篇文章。

5）bulk型的操作（一次操作多个regulator）

```
   1: int regulator_bulk_register_supply_alias(struct device *dev,
```

```
   2:                                          const char *const *id,
```

```
   3:                                          struct device *alias_dev,
```

```
   4:                                          const char *const *alias_id,
```

```
   5:                                          int num_id);
```

```
   6: void regulator_bulk_unregister_supply_alias(struct device *dev,
```

```
   7:                                             const char * const *id, int num_id);
```

```
   8: int __must_check regulator_bulk_get(struct device *dev, int num_consumers,
```

```
   9:                                     struct regulator_bulk_data *consumers);
```

```
  10: int __must_check devm_regulator_bulk_get(struct device *dev, int num_consumers,
```

```
  11:                                          struct regulator_bulk_data *consumers);
```

```
  12: int __must_check regulator_bulk_enable(int num_consumers,
```

```
  13:                                        struct regulator_bulk_data *consumers);
```

```
  14: int regulator_bulk_disable(int num_consumers,
```

```
  15:                            struct regulator_bulk_data *consumers);
```

```
  16: int regulator_bulk_force_disable(int num_consumers,
```

```
  17:                            struct regulator_bulk_data *consumers);
```

```
  18: void regulator_bulk_free(int num_consumers,
```

```
  19:                          struct regulator_bulk_data *consumers);
```

6）notifier相关的接口

```
   1: int regulator_register_notifier(struct regulator *regulator,
```

```
   2:                               struct notifier_block *nb);
```

```
   3: int regulator_unregister_notifier(struct regulator *regulator,
```

```
   4:                                 struct notifier_block *nb);
```

> 如果consumer关心某个regulator的状态变化，可以通过上面接口注册一个notifier。

7）其它接口

```
   1: /* driver data - core doesn't touch */
```

```
   2: void *regulator_get_drvdata(struct regulator *regulator);
```

```
   3: void regulator_set_drvdata(struct regulator *regulator, void *data);
```

> 用于设置和获取driver的私有数据。

**4.2 consumer模块向用户空间consumer提供的接口**

用户空间程序可以通过sysfs接口，使用regulator，就像内核空间consumer一样。这些接口由“drivers/regulator/userspace-consumer.c”实现，主要包括：

> sysfs目录位置：/sys/devices/platform/reg-userspace-consumer。
>
> name，读取可以获取该regulator的名字。
>
> state，读取，可以获取该regulator的状态（enabled/disabled）；写入可以改变regulator的状态（enabled或者1使能，disabled或者0禁止）。

**4.3 machine模块向regulator driver提供的接口**

machine模块主要提供struct regulator\_init\_data、struct regulation\_constraints constraints等数据结构，用于描述板级的regulator配置，具体可参考3.1中介绍。

**4.4 driver模块向regulator driver提供的接口**

regulator framework向regulator driver提供的接口位于“include/linux/regulator/driver.h”中，包括数据结构抽象、regulator注册等。

1）struct regulator\_desc、struct regulator\_config和struct regulator\_dev

见3.2中的介绍。

2）regulator设备的注册接口

```
   1: struct regulator_dev *
```

```
   2: regulator_register(const struct regulator_desc *regulator_desc,
```

```
   3:                    const struct regulator_config *config);
```

```
   4: struct regulator_dev *
```

```
   5: devm_regulator_register(struct device *dev,
```

```
   6:                         const struct regulator_desc *regulator_desc,
```

```
   7:                         const struct regulator_config *config);
```

```
   8: void regulator_unregister(struct regulator_dev *rdev);
```

```
   9: void devm_regulator_unregister(struct device *dev, struct regulator_dev *rdev);
```

见3.2中的介绍。

3）其它接口，请参考后续的文章。

**4.5 core模块向用户空间提供的sysfs接口**

regulator设备在内核中是以regulator class的形式存在的，regulator core通过class->dev\_groups的方式，提供了一些默认的attribute，包括：

> name，读取可以获取该regulator的名字；
>
> num\_users，读取可获取regulator的使用者数目；
>
> type，读取可以获取该regulator的类型（voltage或者current）。

另外，如果regulator driver需要提供更多的attribute（如状态、最大/最小电压等等），可以调用add\_regulator\_attributes接口，主动添加。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/regulator_framework_overview.html)。
