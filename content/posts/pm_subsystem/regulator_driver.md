---
title: "Linux Regulator Framework(2)_regulator driver"
date: 2015-04-16T22:18:58+08:00
url: "/pm_subsystem/regulator_driver.html"
gid: "163"
emlog_type: "blog"
summary: "本文从regulator driver的角度，描述怎样基于regulator framework编写regulator驱动。同时，以此为契机，学习、理解regulator有关的物理特性，以便能够更好的使用它们。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "driver", "framework", "regulator"]
views: 37952
comment_count: 24
aliases:
  - "/pm_subsystem/163.html"
  - "/163.html"
---

#### 1. 前言

本文从regulator driver的角度，描述怎样基于regulator framework编写regulator驱动。同时，以此为契机，学习、理解regulator有关的物理特性，以便能够更好的使用它们。

#### 2. regulator driver的实现步骤

**2.1 确定系统中regulator有关的硬件组成**

提起硬件，最好能有个例子，好在有device tree，一个活生生的硬件拓扑结构。这里以NVIDIA Tegra Dalmore A04开发板为例（regulator有关的device tree位于“arch\arm\boot\dts\tegra114-dalmore.dts”）：

[![regulator hardware block](/content/uploadfile/201504/3c15ff2de0a43ddc2479b2230bda85bd20150416141846.gif "regulator hardware block")](/content/uploadfile/201504/a53264975f020e1bf255e36d9c66bb8520150416141845.gif)这里的regulator结构是相当复杂的，其中彩色框代表最终的regulator抽象，它的前一级表示regulator的载体（可以是PMIC、CPU、等等）。下面将会详细说明：

> a）CPU通过I2C controller，连接一个降压控制器（TI tps51632），该控制器输出名称为“vdd-cpu”的电压，就称作vdd-cpu regulator吧（因此，在kernel中，regulator是一个虚拟设备）。
>
> b）CPU通过I2C controller，连接一个前端电源管理芯片（TI tps65090），该芯片除了具备充电管理功能外，内置了多个regulator，例如dcdc1、dcdc2等等。
>
> c）CPU通过I2C controller，连接另一个电源管理芯片（TI tps65913），该芯片具有两个功能：GPIO输出和PMIC。PMIC内置了多个regulator，如vddio-ddr、vdd-core等等。
>
> d）CPU内部也集成了一些regulator，如vdd\_ac\_bat等等。

注1：单纯从硬件的角度看，是不存在图中"regulators“、PMIC等实体的，它们的出现，已经包含了软件设计的思路。之所以画在这里，是方便后面的描述。

**2.2 使用DTS，将硬件拓扑呈现出来**

我们都知道，DTS的功能是描述设备的拓扑结构，并在系统初始化的时候，为被描述的设备创建并注册对应的platform device，最终和相应的platform driver相遇，执行其probe接口，实现设备的枚举功能。但是，在这些基本原则之外，还需要一些更深的思考：

> DTS节点（node）怎么和设备对应？是以设备的“物理界限”为单位，还是以设备的“功能”为单位？
>
> 是不是所有的“设备”都应该在kernel中创建一个platform device？如果不是，创建的依据是什么？

这些思考在本文的例子（NVIDIA Tegra Dalmore A04的regulator）中体现尤为突出，它的本质是软件设计中的模块划分，从而决定了regulator在DTS中的呈现方式和层次。

1）tps51632

tps51632是一个简单的器件，位于i2c总线下面，包含一个regulator器件，因此其DTS比较简单，如下：

```
   1: /* arch\arm\boot\dts\tegra114-dalmore.dts */
```

```
   2: i2c@7000d000 {
```

```
   3:         status = "okay";
```

```
   4:         clock-frequency = <400000>;
```

```
   5:  
```

```
   6:         tps51632@43 {
```

```
   7:                 compatible = "ti,tps51632";
```

```
   8:                 reg = <0x43>;
```

```
   9:                 regulator-name = "vdd-cpu";
```

```
  10:                 regulator-min-microvolt = <500000>;
```

```
  11:                 regulator-max-microvolt = <1520000>;
```

```
  12:                 regulator-boot-on;
```

```
  13:                 regulator-always-on;
```

```
  14:         };
```

```
  15:         ...
```

```
  16: }
```

> i2c控制器的node为[“i2c@7000d000](mailto:“i2c@7000d000)”，tps51632是其下的一个子node，名称为[“tps51632@43](mailto:“tps51632@43)”，compatible为“ti,tps51632”。tps51632下面以“regulator-”为前缀的字段，是regulator特有的字段，后面会统一介绍。
>
> 注2：为什么[“i2c@7000d000](mailto:“i2c@7000d000)”中没有compatible字段？其实是有的，可参考“arch\arm\boot\dts\tegra114.dtsi”，DTC在编译DTS时，会将这两个文件中的node合并。
>
> 注3：kernel在初始化时，只会为二级node（即“/”下面的节点，本文的例子是[“i2c@7000d000](mailto:“i2c@7000d000)”）创建platform设备，至于三级node（这里的[“tps51632@43](mailto:“tps51632@43)”），则由其bus（i2c）创建。后面我们会遇到其它的情况，到时再介绍。

2）tps65090

tps65090相对比较复杂，它位于相同的i2c总线下面，但包含两个相对复杂的功能实体，charger和PMIC，我们看看其DTS怎么写的：

```
   1: i2c@7000d000 {
```

```
   2:         status = "okay";
```

```
   3:         ...
```

```
   4:  
```

```
   5:         tps65090@48 {
```

```
   6:                 compatible = "ti,tps65090";
```

```
   7:                 reg = <0x48>;
```

```
   8:                 ...
```

```
   9:  
```

```
  10:                 charger: charger {
```

```
  11:                         compatible = "ti,tps65090-charger";
```

```
  12:                         ti,enable-low-current-chrg;
```

```
  13:                 };
```

```
  14:                 
```

```
  15:                 regulators {
```

```
  16:                         tps65090_dcdc1_reg: dcdc1 {
```

```
  17:                                 regulator-name = "vdd-sys-5v0";
```

```
  18:                                 regulator-always-on;
```

```
  19:                                 regulator-boot-on;
```

```
  20:                         };
```

```
  21:                 
```

```
  22:                         tps65090_dcdc2_reg: dcdc2 {
```

```
  23:                                 regulator-name = "vdd-sys-3v3";
```

```
  24:                                 regulator-always-on;
```

```
  25:                                 regulator-boot-on;
```

```
  26:                         };
```

```
  27:                         ...
```

```
  28:                 }
```

```
  29:         }
```

```
  30: }
```

> 和tps51632类似，但它下面又包含了两个子node：charger和regulators。其中charger竟然还有compatible字段。
>
> 回忆一下上面“注3”，kernel只会为"i2c@7000d000”创建platform device，[“tps65090@48](mailto:“tps65090@48)”则由i2c core创建，那么它下面的子node呢？一定是tps65090 driver处理了，感兴趣的读者可以阅读“drivers/mfd/tps65090.c”、“drivers/power/tps65090-charger.c”和“drivers/regulator/tps65090-regulator.c”，这里面还涉及了MFD（multi-function device，多功能设备），很有意思。
>
> 回到本文的主题上，虽然这里的regulators没有compatible字段，也会创建相应的platform device（具体可参考“drivers/mfd/tps65090.c”），这从侧面回答了上面的一个思考：从物理范畴，tps65090是一个独立的设备，但它内部有两个功能模块，因此会存在两个platform device。
>
> 再来看regulators中子node----regulator，由于数量比较多，就没必要创建platform device了。同样，“regulator-”为前缀的字段，是regulator特有的字段，后面统一介绍。

3）tps65913，和tps65090类似，不再介绍。

4）CPU中的regulator

这一类regulator比较特殊，直接集成在CPU内部，DTS如下：

```
   1: regulators {
```

```
   2:         compatible = "simple-bus";
```

```
   3:         #address-cells = <1>;
```

```
   4:         #size-cells = <0>;
```

```
   5:  
```

```
   6:         vdd_ac_bat_reg: regulator@0 {
```

```
   7:                 compatible = "regulator-fixed";
```

```
   8:                 reg = <0>;
```

```
   9:                 regulator-name = "vdd_ac_bat";
```

```
  10:                 regulator-min-microvolt = <5000000>;
```

```
  11:                 regulator-max-microvolt = <5000000>;
```

```
  12:                 regulator-always-on;
```

```
  13:         };
```

```
  14:  
```

```
  15:         dvdd_ts_reg: regulator@1 {
```

```
  16:                 compatible = "regulator-fixed";
```

```
  17:                 reg = <1>;
```

```
  18:                 regulator-name = "dvdd_ts";
```

```
  19:                 regulator-min-microvolt = <1800000>;
```

```
  20:                 regulator-max-microvolt = <1800000>;
```

```
  21:                 enable-active-high;
```

```
  22:                 gpio = <&gpio TEGRA_GPIO(H, 5) GPIO_ACTIVE_HIGH>;
```

```
  23:         };
```

```
  24:         ...
```

```
  25: };
```

> 在回到刚才的话题上，kernel只为二级node创建platform device（这里的“regulators”），那三级node（一个个的regulator）呢？没有相对标准的bus帮它们创建怎么办？借助“simple-bus”，具体可以参考of\_platform\_bus\_create（“[*Device* *Tree*(三):代码分析](/device_model/dt-code-analysis.html)”）。
>
> 另外，这里的例子比较简单，都是fixed regulator，regulator framework core可以帮忙实现fixed类型的regulator的驱动，后面会说明。

**2.3 编写与DTS节点对应的driver**

这些driver的存在形式是多种多样的，但所做的工作基本类似：

1）初始化regulator的宿主（如上面的tps5163、PMIC、等等），最终的目的是，通过宿主提供的接口，修改regulator的输出。

2）初始化用于描述regulator的静态信息（struct regulator\_desc）和动态信息（struct regulator\_config），并以这二者为参数，调用regulator\_register接口，将regulator注册到kernel中。

3）静态信息中包含regulator的操作函数集（struct regulator\_ops），后续regulator的控制，将会由regulator framework core直接调用这些回调函数完成。

4）后面的事情，例如sysfs attribute创建等，就交给regulator framework core了。

#### 3. DTS相关的实现逻辑

**3.1 DTS的内容**

回忆一下“[Linux Regulator Framework(1)\_概述](/pm_subsystem/regulator_framework_overview.html)”中介绍的machine的主要功能：使用软件语言（struct regulator\_init\_data），静态的描述regulator在板级的物理现状。对regulator driver而言，DTS主要用于配置regulator的init data。先看一下struct regulator\_init\_data：

```
   1: /**
```

```
   2:  * struct regulator_init_data - regulator platform initialisation data.
```

```
   3:  *
```

```
   4:  * Initialisation constraints, our supply and consumers supplies.
```

```
   5:  *
```

```
   6:  * @supply_regulator: Parent regulator.  Specified using the regulator name
```

```
   7:  *                    as it appears in the name field in sysfs, which can
```

```
   8:  *                    be explicitly set using the constraints field 'name'.
```

```
   9:  *
```

```
  10:  * @constraints: Constraints.  These must be specified for the regulator to
```

```
  11:  *               be usable.
```

```
  12:  * @num_consumer_supplies: Number of consumer device supplies.
```

```
  13:  * @consumer_supplies: Consumer device supply configuration.
```

```
  14:  *
```

```
  15:  * @regulator_init: Callback invoked when the regulator has been registered.
```

```
  16:  * @driver_data: Data passed to regulator_init.
```

```
  17:  */
```

```
  18: struct regulator_init_data {
```

```
  19:         const char *supply_regulator;        /* or NULL for system supply */
```

```
  20:  
```

```
  21:         struct regulation_constraints constraints;
```

```
  22:  
```

```
  23:         int num_consumer_supplies;
```

```
  24:         struct regulator_consumer_supply *consumer_supplies;
```

```
  25:  
```

```
  26:         /* optional regulator machine specific init */
```

```
  27:         int (*regulator_init)(void *driver_data);
```

```
  28:         void *driver_data;      /* core does not touch this */
```

```
  29: };
```

> supply\_regulator，该regulator的前级regulator，一般在regulator driver中直接指定；
>
> constraints，该regulator的使用限制，由DTS配置，并可以借助regulator core提供的辅助API（regulator\_of\_get\_init\_data）自动解析。后面会详细介绍；
>
> num\_consumer\_supplies、consumer\_supplies，使用该regulator的consumer的个数，及其设备名和supply名的map。用于建立consumer设备和regulator之间的关联，后面介绍consumer DTS时再详细说明；
>
> regulator\_init，regulator的init回调，由regulator driver提供，并在regulator注册时调用；
>
> driver\_data，保存driver的私有数据，并在调用regulator\_init时传入。

看来DTS的内容都在struct regulation\_constraints中，该结构保存了该regulator所有的物理限制，如下：

```
   1: struct regulation_constraints {
```

```
   2:  
```

```
   3:         const char *name;
```

```
   4:  
```

```
   5:         /* voltage output range (inclusive) - for voltage control */
```

```
   6:         int min_uV;
```

```
   7:         int max_uV;
```

```
   8:  
```

```
   9:         int uV_offset;
```

```
  10:  
```

```
  11:         /* current output range (inclusive) - for current control */
```

```
  12:         int min_uA;
```

```
  13:         int max_uA;
```

```
  14:  
```

```
  15:         /* valid regulator operating modes for this machine */
```

```
  16:         unsigned int valid_modes_mask;
```

```
  17:  
```

```
  18:         /* valid operations for regulator on this machine */
```

```
  19:         unsigned int valid_ops_mask;
```

```
  20:  
```

```
  21:         /* regulator input voltage - only if supply is another regulator */
```

```
  22:         int input_uV;
```

```
  23:  
```

```
  24:         /* regulator suspend states for global PMIC STANDBY/HIBERNATE */
```

```
  25:         struct regulator_state state_disk;
```

```
  26:         struct regulator_state state_mem;
```

```
  27:         struct regulator_state state_standby;
```

```
  28:         suspend_state_t initial_state; /* suspend state to set at init */
```

```
  29:  
```

```
  30:         /* mode to set on startup */
```

```
  31:         unsigned int initial_mode;
```

```
  32:  
```

```
  33:         unsigned int ramp_delay;
```

```
  34:         unsigned int enable_time;
```

```
  35:  
```

```
  36:         /* constraint flags */
```

```
  37:         unsigned always_on:1;   /* regulator never off when system is on */
```

```
  38:         unsigned boot_on:1;     /* bootloader/firmware enabled regulator */
```

```
  39:         unsigned apply_uV:1;    /* apply uV constraint if min == max */
```

```
  40:         unsigned ramp_disable:1; /* disable ramp delay */
```

```
  41: };
```

> name，用于描述该constraints；
>
> min\_uV、max\_uV，输出电压的范围，[min\_uV, max\_uV]，单位为uV。只对voltage regulator有效；
>
> uV\_offset，consumer看到的电压和实际电压之间的偏移值。通常用于补偿压降。只对voltage regulator有效；
>
> min\_uA、max\_uA，输出电流的范围，[min\_uA, max\_uA]，单位为uA。只对current regulator有效；
>
> valid\_modes\_mask，regulator mode相关的内容，和DTS无关，后面再解释；
>
> valid\_ops\_mask，该regulator支持哪些操作，以bit mask的形式提供，包括：
>   
>  REGULATOR\_CHANGE\_VOLTAGE，可以改变输出电压；
>   
>  REGULATOR\_CHANGE\_CURRENT，可以改变输出电流；
>   
>  REGULATOR\_CHANGE\_MODE，可以修改mode，后面再介绍；
>   
>  REGULATOR\_CHANGE\_STATUS，可以enable/disable；
>   
>  REGULATOR\_CHANGE\_DRMS，支持Dynamic Regulator Mode Switching（DRMS），可以动态的调整regulator的mode，有关mode描述可参考5.3章节；
>   
>  REGULATOR\_CHANGE\_BYPASS，支持bypass模式。
>
> input\_uV，如果该regulator的输入是另一个regulator，该字段指定regulator期望的输入电压；
>
> state\_xxx、initial\_state，regulator电源管理有关的字段，后面会专门介绍；
>
> initial\_mode，初始mode，具体请参考5.3节的介绍；
>
> always\_on，是否一直保持使能状态；
>
> boot\_on，是否在启动时使能；
>
> rapm\_delay，由于模拟器件的特性，电压改变，需要一定的生效时间。在一定的范围内，生效时间和电压的变化值成比例。该变量就是描述regulator器件的这个特性，单位为uV/us，即1us可以产生多大的电压变化。在rapm\_disable不为1的情况下，当consumer要求改变电压时，regulator framework core会根据该变量，以及电压改变量，计算出需要等待的时间，进行延时操作；
>
> rapm\_disable，是否禁止延时操作；
>
> enable time，regulator的开启时间，单位为us。consumer enable regulator时，regulator framework会根据该变量进行延时操作；
>
> apply\_uV，如果min\_uV和max\_uV相同，该变量指示“在regulator注册到kernel时，是否将电压设置为min\_uV/max\_uV。

结合struct regulation\_constraints结构，我们解释一下2.2小节中tps51632的DTS：

```
   1: tps51632@43 {
```

```
   2:         compatible = "ti,tps51632";
```

```
   3:         reg = <0x43>;
```

```
   4:         regulator-name = "vdd-cpu";
```

```
   5:         regulator-min-microvolt = <500000>;
```

```
   6:         regulator-max-microvolt = <1520000>;
```

```
   7:         regulator-boot-on;
```

```
   8:         regulator-always-on;
```

```
   9: };
```

> regulator-name，对应struct regulation\_constraints中name；
>
> regulator-min-microvolt，对应struct regulation\_constraints中的min\_uV；
>
> regulator-max-microvolt，对应struct regulation\_constraints中的max\_uV；
>
> regulator-boot-on，对应struct regulation\_constraints中的boot\_on；
>
> regulator-always-on，对应struct regulation\_constraints中的always\_on。
>
> 其它的字段，可以根据实际情况，自行添加，具体可参考“Documentation/devicetree/bindings/regulator/regulator.txt”中的描述。

**3.2 DTS的解析**

regulator的DTS信息，可以通过两种方法解析：

1）在regulator注册前，调用of\_get\_regulator\_init\_data接口自行解析，该接口的实现如下：

```
   1: struct regulator_init_data *of_get_regulator_init_data(struct device *dev,
```

```
   2:                                                 struct device_node *node)
```

```
   3: {
```

```
   4:         struct regulator_init_data *init_data;
```

```
   5:  
```

```
   6:         if (!node)
```

```
   7:                 return NULL;
```

```
   8:  
```

```
   9:         init_data = devm_kzalloc(dev, sizeof(*init_data), GFP_KERNEL);
```

```
  10:         if (!init_data)
```

```
  11:                 return NULL; /* Out of memory? */
```

```
  12:  
```

```
  13:         of_get_regulation_constraints(node, &init_data);
```

```
  14:         return init_data;
```

```
  15: }
```

```
  16: EXPORT_SYMBOL_GPL(of_get_regulator_init_data);
```

> 该接口有两个输入参数：设备指针，以及包含了DTS信息的node指针（以3.1中的例子，即[“tps51632@43](mailto:“tps51632@43)”所在的node）。
>
> 它会分配一个struct regulator\_init\_data变量，并调用of\_get\_regulation\_constraints解析DTS，把结果保存在该变量中。
>
> 最后返回struct regulator\_init\_data变量的地址。

2）在regulator注册时，由regulator\_register调用regulator\_of\_get\_init\_data帮忙解析，该接口的实现如下：

```
   1: struct regulator_init_data *regulator_of_get_init_data(struct device *dev,
```

```
   2:                                             const struct regulator_desc *desc,
```

```
   3:                                             struct device_node **node)
```

```
   4: {
```

```
   5:         struct device_node *search, *child;
```

```
   6:         struct regulator_init_data *init_data = NULL;
```

```
   7:         const char *name;
```

```
   8:  
```

```
   9:         if (!dev->of_node || !desc->of_match)
```

```
  10:                 return NULL;
```

```
  11:  
```

```
  12:         if (desc->regulators_node)
```

```
  13:                 search = of_get_child_by_name(dev->of_node,
```

```
  14:                                               desc->regulators_node);
```

```
  15:         else
```

```
  16:                 search = dev->of_node;
```

```
  17:  
```

```
  18:         if (!search) {
```

```
  19:                 dev_dbg(dev, "Failed to find regulator container node '%s'\n",
```

```
  20:                         desc->regulators_node);
```

```
  21:                 return NULL;
```

```
  22:         }
```

```
  23:  
```

```
  24:         for_each_child_of_node(search, child) {
```

```
  25:                 name = of_get_property(child, "regulator-compatible", NULL);
```

```
  26:                 if (!name)
```

```
  27:                         name = child->name;
```

```
  28:  
```

```
  29:                 if (strcmp(desc->of_match, name))
```

```
  30:                         continue;
```

```
  31:  
```

```
  32:                 init_data = of_get_regulator_init_data(dev, child);
```

```
  33:                 if (!init_data) {
```

```
  34:                         dev_err(dev,
```

```
  35:                                 "failed to parse DT for regulator %s\n",
```

```
  36:                                 child->name);
```

```
  37:                         break;
```

```
  38:                 }
```

```
  39:  
```

```
  40:                 of_node_get(child);
```

```
  41:                 *node = child;
```

```
  42:                 break;
```

```
  43:         }
```

```
  44:         of_node_put(search);
```

```
  45:  
```

```
  46:         return init_data;
```

```
  47: }
```

> 与of\_get\_regulator\_init\_data不同的是，该接口以struct regulator\_desc指针为参数，该参数提供了regulator DTS有关的搜索信息（desc->of\_match），根据这些信息，可以获得包含regulator信息的DTS node。
>
> 它本质上是一种通用的DTS匹配逻辑（和kernel解析platform device的标准资源类似），大致如下：
>
> a）调用者提供parent node（struct device指针中，代表regulators的宿主设备，如上面的[tps65090@48](mailto:tps65090@48)），以及该regulator在DTS中的名称（由desc->of\_match提供）。
>
> b）还可以在struct regulator\_desc中提供包含regulator DTS信息的node名称（可选，用于regulator不直接在parent node下的情况）。
>
> c）以parent device的node，或者指定的子node为基准，查找其下所有的node，如果node的名字或者“regulator-compatible”字段和desc->of\_match匹配，则调用of\_get\_regulator\_init\_data从中解析DTS信息。

总结：1、2两种DTS解析的方法，各有优缺点：1直接，方便，容易理解，但会有冗余代码；2简洁，但需要regulator driver开发者非常熟悉解析的原理，并以此设计DTS和struct regulator\_desc变量。大家可以根据实际情况，灵活使用。

#### 4. 主要数据结构

**4.1 struct regulator\_desc**

在注册regulator的时候，需要使用struct regulator\_desc结构提供该regulator的静态描述。所谓的静态，是指这些描述不会在运行时改变，代表了设备的一种属性，如下：

```
   1: /* include/linux/regulator/driver.h */
```

```
   2:  
```

```
   3: struct regulator_desc {
```

```
   4:         const char *name;
```

```
   5:         const char *supply_name;
```

```
   6:         const char *of_match;
```

```
   7:         const char *regulators_node;
```

```
   8:         int id;
```

```
   9:         bool continuous_voltage_range;
```

```
  10:         unsigned n_voltages;
```

```
  11:         const struct regulator_ops *ops;
```

```
  12:         int irq;
```

```
  13:         enum regulator_type type;
```

```
  14:         struct module *owner;
```

```
  15:  
```

```
  16:         unsigned int min_uV;
```

```
  17:         unsigned int uV_step;
```

```
  18:         unsigned int linear_min_sel;
```

```
  19:         int fixed_uV;
```

```
  20:         unsigned int ramp_delay;
```

```
  21:  
```

```
  22:         const struct regulator_linear_range *linear_ranges;
```

```
  23:         int n_linear_ranges;
```

```
  24:  
```

```
  25:         const unsigned int *volt_table;
```

```
  26:  
```

```
  27:         unsigned int vsel_reg;
```

```
  28:         unsigned int vsel_mask;
```

```
  29:         unsigned int apply_reg;
```

```
  30:         unsigned int apply_bit;
```

```
  31:         unsigned int enable_reg;
```

```
  32:         unsigned int enable_mask;
```

```
  33:         unsigned int enable_val;
```

```
  34:         unsigned int disable_val;
```

```
  35:         bool enable_is_inverted;
```

```
  36:         unsigned int bypass_reg;
```

```
  37:         unsigned int bypass_mask;
```

```
  38:         unsigned int bypass_val_on;
```

```
  39:         unsigned int bypass_val_off;
```

```
  40:  
```

```
  41:         unsigned int enable_time;
```

```
  42:  
```

```
  43:         unsigned int off_on_delay;
```

```
  44: };
```

> name，该regulator的名称，唯一标识该regulator，必须提供；
>
> supply\_name，该regulator的输入regulator的名称；
>
> of\_match、regulators\_node，提供信息，以便在注册的时候自动从DTS中解析init\_data，具体可参考3.2小节的描述；
>
> id，标识该regulator的一个数字；
>
> continuous\_voltage\_range，为true时，表示该regulator可以在一定范围输出连续的电压；
>
> n\_voltages，consumer可以通过ops.list\_voltage()接口，获取该regulator可以输出的电压值。该变量指定可以获取的电压值的个数，后面讲到ops时，再介绍；
>
> ops，该regulator的操作函数集，见后面；
>
> irq，该regulator的中断号（有的话）；
>
> type，该regulator的类型，包括REGULATOR\_VOLTAGE和REGULATOR\_CURRENT两种；
>
> 其它字段，和regulator的输出控制有关，后面会以专题的形式介绍。

struct regulator\_ops提供了regulator的所有操作，如下：

```
   1: struct regulator_ops {
```

```
   2:  
```

```
   3:         /* enumerate supported voltages */
```

```
   4:         int (*list_voltage) (struct regulator_dev *, unsigned selector);
```

```
   5:  
```

```
   6:         /* get/set regulator voltage */
```

```
   7:         int (*set_voltage) (struct regulator_dev *, int min_uV, int max_uV,
```

```
   8:                             unsigned *selector);
```

```
   9:         int (*map_voltage)(struct regulator_dev *, int min_uV, int max_uV);
```

```
  10:         int (*set_voltage_sel) (struct regulator_dev *, unsigned selector);
```

```
  11:         int (*get_voltage) (struct regulator_dev *);
```

```
  12:         int (*get_voltage_sel) (struct regulator_dev *);
```

```
  13:  
```

```
  14:         /* get/set regulator current  */
```

```
  15:         int (*set_current_limit) (struct regulator_dev *,
```

```
  16:                                  int min_uA, int max_uA);
```

```
  17:         int (*get_current_limit) (struct regulator_dev *);
```

```
  18:  
```

```
  19:         /* enable/disable regulator */
```

```
  20:         int (*enable) (struct regulator_dev *);
```

```
  21:         int (*disable) (struct regulator_dev *);
```

```
  22:         int (*is_enabled) (struct regulator_dev *);
```

```
  23:  
```

```
  24:         /* get/set regulator operating mode (defined in consumer.h) */
```

```
  25:         int (*set_mode) (struct regulator_dev *, unsigned int mode);
```

```
  26:         unsigned int (*get_mode) (struct regulator_dev *);
```

```
  27:  
```

```
  28:         /* Time taken to enable or set voltage on the regulator */
```

```
  29:         int (*enable_time) (struct regulator_dev *);
```

```
  30:         int (*set_ramp_delay) (struct regulator_dev *, int ramp_delay);
```

```
  31:         int (*set_voltage_time_sel) (struct regulator_dev *,
```

```
  32:                                      unsigned int old_selector,
```

```
  33:                                      unsigned int new_selector);
```

```
  34:  
```

```
  35:         /* report regulator status ... most other accessors report
```

```
  36:          * control inputs, this reports results of combining inputs
```

```
  37:          * from Linux (and other sources) with the actual load.
```

```
  38:          * returns REGULATOR_STATUS_* or negative errno.
```

```
  39:          */
```

```
  40:         int (*get_status)(struct regulator_dev *);
```

```
  41:  
```

```
  42:         /* get most efficient regulator operating mode for load */
```

```
  43:         unsigned int (*get_optimum_mode) (struct regulator_dev *, int input_uV,
```

```
  44:                                           int output_uV, int load_uA);
```

```
  45:  
```

```
  46:         /* control and report on bypass mode */
```

```
  47:         int (*set_bypass)(struct regulator_dev *dev, bool enable);
```

```
  48:         int (*get_bypass)(struct regulator_dev *dev, bool *enable);
```

```
  49:         
```

```
  50:         /* the operations below are for configuration of regulator state when
```

```
  51:          * its parent PMIC enters a global STANDBY/HIBERNATE state */
```

```
  52:         
```

```
  53:         /* set regulator suspend voltage */
```

```
  54:         int (*set_suspend_voltage) (struct regulator_dev *, int uV);
```

```
  55:         
```

```
  56:         /* enable/disable regulator in suspend state */
```

```
  57:         int (*set_suspend_enable) (struct regulator_dev *);
```

```
  58:         int (*set_suspend_disable) (struct regulator_dev *);
```

```
  59:         
```

```
  60:         /* set regulator suspend operating mode (defined in consumer.h) */
```

```
  61:         int (*set_suspend_mode) (struct regulator_dev *, unsigned int mode);
```

```
  62: };
```

> 这些回调函数的具体意义，请参考后续的描述。

**4.2 struct regulator\_config**

struct regulator\_config保存了regulator的动态信息，所谓的动态信息，是指那些会在driver运行过程中改变、或者driver运行后才会确定的信息，如下：

```
   1: struct regulator_config {
```

```
   2:         struct device *dev;
```

```
   3:         const struct regulator_init_data *init_data;
```

```
   4:         void *driver_data;
```

```
   5:         struct device_node *of_node;
```

```
   6:         struct regmap *regmap;
```

```
   7:  
```

```
   8:         int ena_gpio;
```

```
   9:         unsigned int ena_gpio_invert:1;
```

```
  10:         unsigned int ena_gpio_flags;
```

```
  11: };
```

> dev，对应的struct device指针。会在regulator\_register时，由regulator core分配，保存在此，以便后续使用；
>
> init\_data，init data指针，在解析DTS后，保存在此，以便后续使用；
>
> of\_node，可以为空；
>
> regmap，参考后续描述；
>
> ena\_gpio、ena\_gpio\_invert、ena\_gpio\_flags，控制regulator使能的GPIO及其active极性。

**4.3 struct regulator\_dev**

struct regulator\_dev是regulator设备的抽象，当driver以struct regulator\_desc、struct regulator\_config两个类型的参数，调用regulator\_register将regulator注册到kernel之后，regulator就会分配一个struct regulator\_dev变量，后续所有的regulator操作，都将以该变量为对象。

```
   1: struct regulator_dev {
```

```
   2:         const struct regulator_desc *desc;
```

```
   3:         int exclusive;
```

```
   4:         u32 use_count;
```

```
   5:         u32 open_count;
```

```
   6:         u32 bypass_count;
```

```
   7:  
```

```
   8:         /* lists we belong to */
```

```
   9:         struct list_head list; /* list of all regulators */
```

```
  10:  
```

```
  11:         /* lists we own */
```

```
  12:         struct list_head consumer_list; /* consumers we supply */
```

```
  13:  
```

```
  14:         struct blocking_notifier_head notifier;
```

```
  15:         struct mutex mutex; /* consumer lock */
```

```
  16:         struct module *owner;
```

```
  17:         struct device dev;
```

```
  18:         struct regulation_constraints *constraints;
```

```
  19:         struct regulator *supply;       /* for tree */
```

```
  20:         struct regmap *regmap;
```

```
  21:  
```

```
  22:         struct delayed_work disable_work;
```

```
  23:         int deferred_disables;
```

```
  24:  
```

```
  25:         void *reg_data;         /* regulator_dev data */
```

```
  26:  
```

```
  27:         struct dentry *debugfs;
```

```
  28:  
```

```
  29:         struct regulator_enable_gpio *ena_pin;
```

```
  30:         unsigned int ena_gpio_state:1;
```

```
  31:  
```

```
  32:         /* time when this regulator was disabled last time */
```

```
  33:         unsigned long last_off_jiffy;
```

```
  34: };
```

> desc，保存了regulator静态描述信息的指针（从这个角度看，所谓的静态描述，其变量必须为全局变量）；
>
> exclusive、use\_count、open\_count、bypass\_count，一些状态记录；
>
> constraints，保存了regulator的constraints指针；
>
> supply，该regulator的supply；
>
> 等等。

#### 5 实现逻辑分析

本章简单的分析一下regulator driver相关的实现逻辑。如果要理解有些逻辑，必须具备一些regulator的基础知识，因此在需要的时候，会穿插介绍这些知识。

**5.1 regulator core的初始化**

regulator core的初始化操作由regulator\_init接口负责，主要工作包括：

> 1）注册regulator class（/sys/class/regulator/）。
>
> 2）注册用于调试的debugfs。

和power switch class、input class等类似，regulator framework也是一种class，可以称作regulator class。

**5.2 regulator register**

regulator的注册，由regulator\_register/devm\_regulator\_register接口负责，如下：

```
   1: /**
```

```
   2:  * regulator_register - register regulator
```

```
   3:  * @regulator_desc: regulator to register
```

```
   4:  * @config: runtime configuration for regulator
```

```
   5:  *
```

```
   6:  * Called by regulator drivers to register a regulator.
```

```
   7:  * Returns a valid pointer to struct regulator_dev on success
```

```
   8:  * or an ERR_PTR() on error.
```

```
   9:  */
```

```
  10: struct regulator_dev *
```

```
  11: regulator_register(const struct regulator_desc *regulator_desc,
```

```
  12:            const struct regulator_config *config)
```

```
  13: {
```

```
  14:     const struct regulation_constraints *constraints = NULL;
```

```
  15:     const struct regulator_init_data *init_data;
```

```
  16:     static atomic_t regulator_no = ATOMIC_INIT(0);
```

```
  17:     struct regulator_dev *rdev;
```

```
  18:     struct device *dev;
```

```
  19:     int ret, i;
```

```
  20:     const char *supply = NULL;
```

```
  21:  
```

```
  22:     if (regulator_desc == NULL || config == NULL)
```

```
  23:         return ERR_PTR(-EINVAL);
```

```
  24:  
```

```
  25:     dev = config->dev;
```

```
  26:     WARN_ON(!dev);
```

```
  27:  
```

```
  28:     if (regulator_desc->name == NULL || regulator_desc->ops == NULL)
```

```
  29:         return ERR_PTR(-EINVAL);
```

```
  30:  
```

```
  31:     if (regulator_desc->type != REGULATOR_VOLTAGE &&
```

```
  32:         regulator_desc->type != REGULATOR_CURRENT)
```

```
  33:         return ERR_PTR(-EINVAL);
```

```
  34:  
```

```
  35:     /* Only one of each should be implemented */
```

```
  36:     WARN_ON(regulator_desc->ops->get_voltage &&
```

```
  37:         regulator_desc->ops->get_voltage_sel);
```

```
  38:     WARN_ON(regulator_desc->ops->set_voltage &&
```

```
  39:         regulator_desc->ops->set_voltage_sel);
```

```
  40:  
```

```
  41:     /* If we're using selectors we must implement list_voltage. */
```

```
  42:     if (regulator_desc->ops->get_voltage_sel &&
```

```
  43:         !regulator_desc->ops->list_voltage) {
```

```
  44:         return ERR_PTR(-EINVAL);
```

```
  45:     }
```

```
  46:     if (regulator_desc->ops->set_voltage_sel &&
```

```
  47:         !regulator_desc->ops->list_voltage) {
```

```
  48:         return ERR_PTR(-EINVAL);
```

```
  49:     }
```

```
  50:  
```

```
  51:     rdev = kzalloc(sizeof(struct regulator_dev), GFP_KERNEL);
```

```
  52:     if (rdev == NULL)
```

```
  53:         return ERR_PTR(-ENOMEM);
```

```
  54:  
```

```
  55:     init_data = regulator_of_get_init_data(dev, regulator_desc,
```

```
  56:                            &rdev->dev.of_node);
```

```
  57:     if (!init_data) {
```

```
  58:         init_data = config->init_data;
```

```
  59:         rdev->dev.of_node = of_node_get(config->of_node);
```

```
  60:     }
```

```
  61:  
```

```
  62:     mutex_lock(&regulator_list_mutex);
```

```
  63:  
```

```
  64:     mutex_init(&rdev->mutex);
```

```
  65:     rdev->reg_data = config->driver_data;
```

```
  66:     rdev->owner = regulator_desc->owner;
```

```
  67:     rdev->desc = regulator_desc;
```

```
  68:     if (config->regmap)
```

```
  69:         rdev->regmap = config->regmap;
```

```
  70:     else if (dev_get_regmap(dev, NULL))
```

```
  71:         rdev->regmap = dev_get_regmap(dev, NULL);
```

```
  72:     else if (dev->parent)
```

```
  73:         rdev->regmap = dev_get_regmap(dev->parent, NULL);
```

```
  74:     INIT_LIST_HEAD(&rdev->consumer_list);
```

```
  75:     INIT_LIST_HEAD(&rdev->list);
```

```
  76:     BLOCKING_INIT_NOTIFIER_HEAD(&rdev->notifier);
```

```
  77:     INIT_DELAYED_WORK(&rdev->disable_work, regulator_disable_work);
```

```
  78:  
```

```
  79:     /* preform any regulator specific init */
```

```
  80:     if (init_data && init_data->regulator_init) {
```

```
  81:         ret = init_data->regulator_init(rdev->reg_data);
```

```
  82:         if (ret < 0)
```

```
  83:             goto clean;
```

```
  84:     }
```

```
  85:  
```

```
  86:     /* register with sysfs */
```

```
  87:     rdev->dev.class = &regulator_class;
```

```
  88:     rdev->dev.parent = dev;
```

```
  89:     dev_set_name(&rdev->dev, "regulator.%d",
```

```
  90:              atomic_inc_return(&regulator_no) - 1);
```

```
  91:     ret = device_register(&rdev->dev);
```

```
  92:     if (ret != 0) {
```

```
  93:         put_device(&rdev->dev);
```

```
  94:         goto clean;
```

```
  95:     }
```

```
  96:  
```

```
  97:     dev_set_drvdata(&rdev->dev, rdev);
```

```
  98:  
```

```
  99:     if (config->ena_gpio && gpio_is_valid(config->ena_gpio)) {
```

```
 100:         ret = regulator_ena_gpio_request(rdev, config);
```

```
 101:         if (ret != 0) {
```

```
 102:             rdev_err(rdev, "Failed to request enable GPIO%d: %d\n",
```

```
 103:                  config->ena_gpio, ret);
```

```
 104:             goto wash;
```

```
 105:         }
```

```
 106:  
```

```
 107:         if (config->ena_gpio_flags & GPIOF_OUT_INIT_HIGH)
```

```
 108:             rdev->ena_gpio_state = 1;
```

```
 109:  
```

```
 110:         if (config->ena_gpio_invert)
```

```
 111:             rdev->ena_gpio_state = !rdev->ena_gpio_state;
```

```
 112:     }
```

```
 113:  
```

```
 114:     /* set regulator constraints */
```

```
 115:     if (init_data)
```

```
 116:         constraints = &init_data->constraints;
```

```
 117:  
```

```
 118:     ret = set_machine_constraints(rdev, constraints);
```

```
 119:     if (ret < 0)
```

```
 120:         goto scrub;
```

```
 121:  
```

```
 122:     /* add attributes supported by this regulator */
```

```
 123:     ret = add_regulator_attributes(rdev);
```

```
 124:     if (ret < 0)
```

```
 125:         goto scrub;
```

```
 126:  
```

```
 127:     if (init_data && init_data->supply_regulator)
```

```
 128:         supply = init_data->supply_regulator;
```

```
 129:     else if (regulator_desc->supply_name)
```

```
 130:         supply = regulator_desc->supply_name;
```

```
 131:  
```

```
 132:     if (supply) {
```

```
 133:         struct regulator_dev *r;
```

```
 134:  
```

```
 135:         r = regulator_dev_lookup(dev, supply, &ret);
```

```
 136:  
```

```
 137:         if (ret == -ENODEV) {
```

```
 138:             /*
```

```
 139:              * No supply was specified for this regulator and
```

```
 140:              * there will never be one.
```

```
 141:              */
```

```
 142:             ret = 0;
```

```
 143:             goto add_dev;
```

```
 144:         } else if (!r) {
```

```
 145:             dev_err(dev, "Failed to find supply %s\n", supply);
```

```
 146:             ret = -EPROBE_DEFER;
```

```
 147:             goto scrub;
```

```
 148:         }
```

```
 149:  
```

```
 150:         ret = set_supply(rdev, r);
```

```
 151:         if (ret < 0)
```

```
 152:             goto scrub;
```

```
 153:  
```

```
 154:         /* Enable supply if rail is enabled */
```

```
 155:         if (_regulator_is_enabled(rdev)) {
```

```
 156:             ret = regulator_enable(rdev->supply);
```

```
 157:             if (ret < 0)
```

```
 158:                 goto scrub;
```

```
 159:         }
```

```
 160:     }
```

```
 161:  
```

```
 162: add_dev:
```

```
 163:     /* add consumers devices */
```

```
 164:     if (init_data) {
```

```
 165:         for (i = 0; i < init_data->num_consumer_supplies; i++) {
```

```
 166:             ret = set_consumer_device_supply(rdev,
```

```
 167:                 init_data->consumer_supplies[i].dev_name,
```

```
 168:                 init_data->consumer_supplies[i].supply);
```

```
 169:             if (ret < 0) {
```

```
 170:                 dev_err(dev, "Failed to set supply %s\n",
```

```
 171:                     init_data->consumer_supplies[i].supply);
```

```
 172:                 goto unset_supplies;
```

```
 173:             }
```

```
 174:         }
```

```
 175:     }
```

```
 176:  
```

```
 177:     list_add(&rdev->list, &regulator_list);
```

```
 178:  
```

```
 179:     rdev_init_debugfs(rdev);
```

```
 180: out:
```

```
 181:     mutex_unlock(&regulator_list_mutex);
```

```
 182:     return rdev;
```

```
 183:  
```

```
 184: unset_supplies:
```

```
 185:     unset_regulator_supplies(rdev);
```

```
 186:  
```

```
 187: scrub:
```

```
 188:     if (rdev->supply)
```

```
 189:         _regulator_put(rdev->supply);
```

```
 190:     regulator_ena_gpio_free(rdev);
```

```
 191:     kfree(rdev->constraints);
```

```
 192: wash:
```

```
 193:     device_unregister(&rdev->dev);
```

```
 194:     /* device core frees rdev */
```

```
 195:     rdev = ERR_PTR(ret);
```

```
 196:     goto out;
```

```
 197:  
```

```
 198: clean:
```

```
 199:     kfree(rdev);
```

```
 200:     rdev = ERR_PTR(ret);
```

```
 201:     goto out;
```

```
 202: }
```

```
 203: EXPORT_SYMBOL_GPL(regulator_register);
```

> 主要工作包括：
>
> 22~49，检查参数的合法性。其中35~49行，涉及到电压控制的方式，后面后详细说明；
>
> 55~60，协助从DTS解析init data，如果解析不到，则使用config中的；
>
> 68~73，协助获取regulator的register map（有的话），并保存在register device指针中。regulator driver会在需要的时候使用（通常是在ops回调函数中）；
>
> 74~77，初始化一些全局变量，consumer\_list用于保存所有的consumer，list用于将自己添加到一个全局的regulator链表（regulator\_list）上，disable\_work是用于disable regulator的work queue；
>
> 86~95，将regulator device注册到kernel；
>
> 99~112，申请regulator enable gpio（有的话），并将相应的信息保存在regulator device指针中；
>
> 114~120，将从DTS中解析的constraints，应用起来（这个过程比较复杂，就不介绍了，感兴趣的读者可以自行分析）；
>
> 123，根据regulator的操作函数集，注册相应的attribute（和[PSY class](/pm_subsystem/psy_class_overview.html)类似）；
>
> 127~160，如果该regulator有supply，根据supply的名字，获取相应的regulator device指针，同时根据supply指针，分配一个struct regulator结构，保存在该regulator的supply指针中。最后，如果该regulator处于使能状态，则需要使能其supply（这些动作，需要以consumer的视角操作，因而需要一个struct regulator变量）；
>
> 162~175，add consumer devices，等到介绍consumer时，再详细描述。

注4：register map是kernel提供的一种管理寄存器的机制，特别是较为复杂的寄存器，如codec等。本文不会过多描述，如需要，会专门写一篇文章介绍该机制。

**5.3 regulator的操作模式（operation mode）**

regulator的主要功能，是输出电压/电流的调整（或改变）。由于模拟器件的特性，电压/电流的改变，是需要一定的时间的。对有些regulator而言，可以工作在不同的模式，这些模式有不同的改变速度，可想而知，较快的速度，有较大的功耗。下面是operation mode定义（位于include/linux/regulator/consumer.h中）：

```
   1: /*
```

```
   2:  * Regulator operating modes.
```

```
   3:  *
```

```
   4:  * Regulators can run in a variety of different operating modes depending on
```

```
   5:  * output load. This allows further system power savings by selecting the
```

```
   6:  * best (and most efficient) regulator mode for a desired load.
```

```
   7:  *
```

```
   8:  * Most drivers will only care about NORMAL. The modes below are generic and
```

```
   9:  * will probably not match the naming convention of your regulator data sheet
```

```
  10:  * but should match the use cases in the datasheet.
```

```
  11:  *
```

```
  12:  * In order of power efficiency (least efficient at top).
```

```
  13:  *
```

```
  14:  *  Mode       Description
```

```
  15:  *  FAST       Regulator can handle fast changes in it's load.
```

```
  16:  *             e.g. useful in CPU voltage & frequency scaling where
```

```
  17:  *             load can quickly increase with CPU frequency increases.
```

```
  18:  *
```

```
  19:  *  NORMAL     Normal regulator power supply mode. Most drivers will
```

```
  20:  *             use this mode.
```

```
  21:  *
```

```
  22:  *  IDLE       Regulator runs in a more efficient mode for light
```

```
  23:  *             loads. Can be used for devices that have a low power
```

```
  24:  *             requirement during periods of inactivity. This mode
```

```
  25:  *             may be more noisy than NORMAL and may not be able
```

```
  26:  *             to handle fast load switching.
```

```
  27:  *
```

```
  28:  *  STANDBY    Regulator runs in the most efficient mode for very
```

```
  29:  *             light loads. Can be used by devices when they are
```

```
  30:  *             in a sleep/standby state. This mode is likely to be
```

```
  31:  *             the most noisy and may not be able to handle fast load
```

```
  32:  *             switching.
```

```
  33:  *
```

```
  34:  * NOTE: Most regulators will only support a subset of these modes. Some
```

```
  35:  * will only just support NORMAL.
```

```
  36:  *
```

```
  37:  * These modes can be OR'ed together to make up a mask of valid register modes.
```

```
  38:  */
```

```
  39:  
```

```
  40: #define REGULATOR_MODE_FAST                     0x1
```

```
  41: #define REGULATOR_MODE_NORMAL                   0x2
```

```
  42: #define REGULATOR_MODE_IDLE                     0x4
```

```
  43: #define REGULATOR_MODE_STANDBY                  0x8
```

相应的，regulator framework提供了一些机制，用于operation mode的操作，包括：

1）struct regulation\_constraints中用于表示初始模式的字段initial\_mode。

2）regulator ops中的set\_mode/get\_mode回调函数。

**5.4 电压操作的两种方式**

kernel抽象了两种电压操作的方法：

1）直接操作电压，对应struct regulator\_ops中的如下回调函数：

```
   1: /* get/set regulator voltage */
```

```
   2: int (*list_voltage) (struct regulator_dev *, unsigned selector);
```

```
   3: int (*set_voltage) (struct regulator_dev *, int min_uV, int max_uV,
```

```
   4:                     unsigned *selector);
```

```
   5: int (*get_voltage) (struct regulator_dev *);
```

> 其中set\_voltage用于将电压设置为min\_uV和max\_uV范围内、和min\_uV最接近的电压。该接口可以返回一个selector参数，用于告知调用者，实际的电压值；
>
> get\_voltage，用于返回当前的电压值；
>
> list\_voltage，以selector为参数，获取对应的电压值。
>
> 注5：有关selector的描述，可参考下面的介绍。

2）selector的形式

regulator driver以selector的形式，反映电压值。selector是一个从0开始的整数，driver提供如下的接口：

```
   1: /* enumerate supported voltages */
```

```
   2: int (*list_voltage) (struct regulator_dev *, unsigned selector);
```

```
   3:  
```

```
   4: int (*map_voltage)(struct regulator_dev *, int min_uV, int max_uV);
```

```
   5: int (*set_voltage_sel) (struct regulator_dev *, unsigned selector);
```

```
   6: int (*get_voltage_sel) (struct regulator_dev *);
```

> list\_voltage，上面已经介绍；
>
> map\_voltage，是和list\_voltage相对的接口，用于将电压范围map成一个selector值；
>
> set\_voltage\_sel/get\_voltage\_sel，以selector的形式，操作电压。

regulator driver可以根据实际情况，选择一种实现方式。

**5.5 regulator framework提供的sysfs接口**

根据regulator提供的ops情况，regulator framework可以通过sysfs提供多种attribute，它们位于/sys/class/regulator/.../目录下，数量相当多，这里就不一一描述了，具体可参考：

[https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-regulator](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-regulator "https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-regulator")

#### 6. 后记

这篇文章写的相当纠结，相当混乱，我相信读者很难看懂……

本以为会很容易写，但里面的知识点太零碎了，以至于无法很好的归纳、抽象、突出重点。崩溃！

时间原因，就先这样了，有机会再回头来整理，希望读者谅解。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/regulator_driver.html)。
