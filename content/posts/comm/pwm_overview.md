---
title: "Linux PWM framework(1)_简介和API描述"
date: 2015-10-11T15:45:37+08:00
url: "/comm/pwm_overview.html"
gid: "217"
emlog_type: "blog"
summary: "\r\n\tPWM是Pulse Width \r\nModulation（脉冲宽度调制）的缩写，是利用微处理器的数字输出来对模拟电路进行控制的一种非常有效的技术，其本质是一种对模拟信号电平进行数字编码的方法。在嵌入式设备中，PWM多用于控制马达、LED、振动器等模拟器件。\r\n\r\n\r\n\tPWM framework是kernel为了方便PWM \r\ndriver开发、PWM使用而抽象出来的一套通用API，之所以要"
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "driver", "pwm"]
views: 43957
comment_count: 20
aliases:
  - "/comm/217.html"
  - "/217.html"
---

#### 1. 前言

PWM是Pulse Width Modulation（脉冲宽度调制）的缩写，是利用微处理器的数字输出来对模拟电路进行控制的一种非常有效的技术，其本质是一种对模拟信号电平进行数字编码的方法。在嵌入式设备中，PWM多用于控制马达、LED、振动器等模拟器件。

PWM framework是kernel为了方便PWM driver开发、PWM使用而抽象出来的一套通用API，之所以要分析该framework，原因如下：

> 1）PWM接口，本质上一种通信协议，和I2C、SPI、USB、WIFI等没有任何差别。因此，本文将会是kernel通信协议有关framework的分析文章的第一篇。
>
> 2）它太简单了！但是，虽然简单，思路却大同小异，因而非常适合做第一篇。
>
> 3）我计划整理显示子系统的分析文章，而PWM，是显示子系统中最基础的那一个。

闲话少说，言归正传！

#### 2. 软件框架及API汇整

PWM framework非常简单，但它同样具备framework的基本特性：对上，为内核其它driver（Consumer）提供使用PWM功能的统一接口；对下，为PWM driver（Provider）提供driver开发的通用方法和API；内部，抽象并实现公共逻辑，屏蔽技术细节。下面我们通过它所提供的API，进一步认识PWM framework。

##### 2.1 向PWM consumer提供的APIs

对consumer而言，关注PWM的如下参数：

1）频率

> PWM的频率决定了所模拟出来的模拟电平的平滑度，通俗的讲，就是逼真度。不同的模拟器件，对期待的频率是有要求的，因此需要具体情况具体对待。
>
> 另外，人耳能感知的频率范围是20Hz~16KHz，因此要注意PWM的频率不要落在这个范围，否则可能会产生莫名其妙的噪声。

2）占空比

占空比，决定了一个周期内PWM信号高低的比率，进而决定了一个周期内的平均电压，也即所模拟的模拟电平的电平值。

3）极性

简单的说，一个PWM信号的极性，决定了是高占空比的信号输出电平高，还是低占空比信号输出电平高。假设一个信号的占空比为100%，如果为正常极性，则输出电平最大，如果为翻转的极性，则输出电平为0。

4）开关

控制PWM信号是否输出。

基于上述需求，linux pwm framework向consumer提供了如下API：

```
  1: /* include/linux/pwm.h */
  2: 
  3: /*
  4:  * pwm_config - change a PWM device configuration
  5:  */
  6: int pwm_config(struct pwm_device *pwm, int duty_ns, int period_ns);
  7: 
  8: /*
  9:  * pwm_enable - start a PWM output toggling
 10:  */
 11: int pwm_enable(struct pwm_device *pwm);
 12: 
 13: /*
 14:  * pwm_disable - stop a PWM output toggling
 15:  */
 16: void pwm_disable(struct pwm_device *pwm);
 17: 
 18: /*
 19:  * pwm_set_polarity - configure the polarity of a PWM signal
 20:  */
 21: int pwm_set_polarity(struct pwm_device *pwm, enum pwm_polarity polarity);
```

> pwm\_config，用于控制PWM输出信号的频率和占空比，其中频率是以周期（period\_ns）的形式配置的，占空比是以有效时间（duty\_ns）的形式配置的。
>
> pwm\_enable/pwm\_disable，用于控制PWM信号输出与否。
>
> pwm\_set\_polarity，可以更改pwm信号的极性，可选参数包括normal（PWM\_POLARITY\_NORMAL）和inversed（极性翻转，PWM\_POLARITY\_INVERSED）两种。

上面的API都以struct pwm\_device类型的指针为操作句柄，该指针抽象了一个PWM设备（consumer不需要关心其内部构成），那么怎么获得PWM句柄呢？使用如下的API：

注1：本文只介绍基于DTS的、新的pwm request系列接口，对于那些旧接口，让它随风而去吧。

```
  1: /* include/linux/pwm.h */
  2: 
  3: struct pwm_device *pwm_get(struct device *dev, const char *con_id);
  4: struct pwm_device *of_pwm_get(struct device_node *np, const char *con_id);
  5: void pwm_put(struct pwm_device *pwm);
  6: 
  7: struct pwm_device *devm_pwm_get(struct device *dev, const char *con_id);
  8: struct pwm_device *devm_of_pwm_get(struct device *dev, struct device_node *np,
  9:                                    const char *con_id);
 10: void devm_pwm_put(struct device *dev, struct pwm_device *pwm);
```

> pwm\_get/devm\_pwm\_get，从指定设备（dev）的DTS节点中，获得对应的PWM句柄。可以通过con\_id指定一个名称，或者会获取和该设备绑定的第一个PWM句柄。设备的DTS文件需要用这样的格式指定所使用的PWM device（具体的形式，还依赖pwm driver的具体实现，后面会再介绍）：
>   
> bl: backlight {
>   
>  pwms = <&pwm 0 5000000 PWM\_POLARITY\_INVERTED>;
>   
>  pwm-names = "backlight";
>   
> };
>   
> 如果“con\_id”为NULL，则返回DTS中“pwms”字段所指定的第一个PWM device；如果“con\_id”不为空，如是“backlight”，则返回和“pwm-names ”字段所指定的name对应的PWM device。
>   
> 上面“pwms”字段各个域的含义如下：
>   
> 1）&pwm，对DTS中pwm节点的引用；
>   
> 2）0，pwm device的设备号，具体需要参考SOC以及pwm driver的实际情况；
>   
> 3）5000000，PWM信号默认的周期，单位是纳秒（ns）；
>   
> 4）PWM\_POLARITY\_INVERTED，可选字段，是否提供由pwm driver决定，表示pwm信号的极性，若为0，则正常极性，若为PWM\_POLARITY\_INVERTED，则反转极性。
>
> of\_pwm\_get/devm\_of\_pwm\_get，和pwm\_get/devm\_pwm\_get类似，区别是可以指定需要从中解析PWM信息的device node，而不是直接指定device指针。

##### 2.2 向PWM provider提供的APIs

接着从PWM provider的角度，看一下PWM framework为provider编写PWM驱动提供了哪些API。

###### 2.2.1 pwm chip

PWM framework使用struct pwm\_chip抽象PWM控制器。通常情况下，在一个SOC中，可以同时支持多路PWM输出（如6路），以便同时控制多个PWM设备。这样每一路PWM输出，可以看做一个PWM设备（由上面struct pwm\_device抽象），没有意外的话，这些PWM设备的控制方式应该类似。PWM framework会统一管理这些PWM设备，将它们归类为一个PWM chip。

struct pwm\_chip的定义如下：

```
  1: /* include/linux/pwm.h */
  2: 
  3: /**
  4:  * struct pwm_chip - abstract a PWM controller
  5:  * @dev: device providing the PWMs
  6:  * @list: list node for internal use
  7:  * @ops: callbacks for this PWM controller
  8:  * @base: number of first PWM controlled by this chip
  9:  * @npwm: number of PWMs controlled by this chip
 10:  * @pwms: array of PWM devices allocated by the framework
 11:  * @can_sleep: must be true if the .config(), .enable() or .disable()
 12:  *             operations may sleep
 13:  */
 14: struct pwm_chip {
 15:         struct device           *dev;
 16:         struct list_head        list;
 17:         const struct pwm_ops    *ops;
 18:         int                     base;
 19:         unsigned int            npwm;
 20: 
 21:         struct pwm_device       *pwms;
 22: 
 23:         struct pwm_device *     (*of_xlate)(struct pwm_chip *pc,
 24:                                             const struct of_phandle_args *args);
 25:         unsigned int            of_pwm_n_cells;
 26:         bool                    can_sleep;
 27: };
```

> dev，该pwm chip对应的设备，一般由pwm driver对应的platform驱动指定。必须提供！
>
> ops，操作PWM设备的回调函数，后面会详细介绍。必须提供！
>
> npwm，该pwm chip可以支持的pwm channel（也可以称作pwm device由struct pwm\_device表示）个数，kernel会根据该number，分配相应个数的struct pwm\_device结构，保存在pwms指针中。必须提供！
>
> pwms，保存所有pwm device的数组，kernel会自行分配，不需要driver关心。
>
> base，在将该chip下所有pwm device组成radix tree时使用，只有旧的pwm\_request接口会使用，因此忽略它吧，编写pwm driver不需要关心。
>
> of\_pwm\_n\_cells，该PWM chip所提供的DTS node的cell，一般是2或者3，例如：为3时，consumer需要在DTS指定pwm number、pwm period和pwm flag三种信息（如2.1中的介绍）；为2时，没有flag信息。
>
> of\_xlate，用于解析consumer中指定的、pwm信息的DTS node的回调函数（如2.1中介绍的，pwms = <&pwm 0 5000000 PWM\_POLARITY\_INVERTED>）。
>
> 注2：一般情况下，of\_pwm\_n\_cells取值为3，或者2（不关心极性），of\_xlate则可以使用kernel提供的of\_pwm\_xlate\_with\_flags（解析of\_pwm\_n\_cells为3的chip）或者of\_pwm\_simple\_xlate（解析of\_pwm\_n\_cells为2的情况）。具体的driver可以根据实际情况修改上述规则，但不到万不得已的时候，不要做这种非标准的、掏力不讨好的事情！（有关of\_xlate的流程，会在下一篇流程分析的文章中介绍。）
>
> can\_sleep，如果ops回调函数中，.config()，.enable()或者.disable()操作会sleep，则要设置该变量。

###### 2.2.2 pwm ops

struct pwm\_ops结构是pwm device有关的操作函数集，如下：

```
  1: /**
  2:  * struct pwm_ops - PWM controller operations
  3:  * @request: optional hook for requesting a PWM
  4:  * @free: optional hook for freeing a PWM
  5:  * @config: configure duty cycles and period length for this PWM
  6:  * @set_polarity: configure the polarity of this PWM
  7:  * @enable: enable PWM output toggling
  8:  * @disable: disable PWM output toggling
  9:  * @dbg_show: optional routine to show contents in debugfs
 10:  * @owner: helps prevent removal of modules exporting active PWMs
 11:  */
 12: struct pwm_ops {
 13:         int                     (*request)(struct pwm_chip *chip,
 14:                                            struct pwm_device *pwm);
 15:         void                    (*free)(struct pwm_chip *chip,
 16:                                         struct pwm_device *pwm);
 17:         int                     (*config)(struct pwm_chip *chip,
 18:                                           struct pwm_device *pwm,
 19:                                           int duty_ns, int period_ns);
 20:         int                     (*set_polarity)(struct pwm_chip *chip,
 21:                                           struct pwm_device *pwm,
 22:                                           enum pwm_polarity polarity);
 23:         int                     (*enable)(struct pwm_chip *chip,
 24:                                           struct pwm_device *pwm);
 25:         void                    (*disable)(struct pwm_chip *chip,
 26:                                            struct pwm_device *pwm);
 27: #ifdef CONFIG_DEBUG_FS
 28:         void                    (*dbg_show)(struct pwm_chip *chip,
 29:                                             struct seq_file *s);
 30: #endif
 31:         struct module           *owner;
 32: };
```

> 这些回调函数的操作对象是具体的pwm device（由struct pwm\_device类型的指针表示），包括：
>
> config，配置pwm device的频率、占空比。必须提供！
>
> enable/disable，使能/禁止pwm信号输出。必须提供！
>
> request/free，不再使用。
>
> set\_polarity，设置pwm信号的极性。可选，具体需要参考of\_pwm\_n\_cells的定义。

###### 2.2.3 pwm device

struct pwm\_device是pwm device的操作句柄，consumer的API调用，会中转到provider的pwm ops回调函数上，provider（及pwm driver）根据pwm device的信息，进行相应的寄存器操作。如下：

```
  1: struct pwm_device {
  2:         const char              *label;
  3:         unsigned long           flags;
  4:         unsigned int            hwpwm;
  5:         unsigned int            pwm;
  6:         struct pwm_chip         *chip;
  7:         void                    *chip_data;
  8: 
  9:         unsigned int            period;         /* in nanoseconds */
 10:         unsigned int            duty_cycle;     /* in nanoseconds */
 11:         enum pwm_polarity       polarity;
 12: };
```

> pwm driver比较关心的字段是：
>
> hwpwm，该pwm device对应的hardware pwm number，可用于寄存器的寻址操作。
>
> period、duty\_cycle、polarity，pwm信号的周期、占空比、极性等信息。

###### 2.2.4 pwmchip\_add/pwmchip\_remove

初始化完成后的pwm chip可以通过pwmchip\_add接口注册到kernel中，之后的事情，pwm driver就不用操心了。该接口的原型如下：

```
  1: int pwmchip_add(struct pwm_chip *chip);
  2: int pwmchip_remove(struct pwm_chip *chip);
```

#### 3. API使用指南

##### 3.1 consumer使用PWM的步骤

基于2.1章节描述的API，可以得到pwm consumer（如pwm backlight driver）使用pwm framework的方法和步骤如下：

1）查看pwm provider所提供的pwm dts binding信息（一般会在“Documentation/devicetree/bindings/pwm”目录中），并以此在该device所在的dts node中添加“pwms ”以及“pwm-names ”相关的配置。例如：

> /\* arch\arm\boot\dts\imx23-evk.dts \*/
>   
> backlight {
>   
>  compatible = "pwm-backlight";
>   
> pwms = <&pwm 2 5000000>;
>   
>  brightness-levels = <0 4 8 16 32 64 128 255>;
>   
>  default-brightness-level = <6>;
>   
> };

其中，&pwm，表示对pwm driver的DTS节点的引用，具体可参考下面3.2章节的介绍。

2）在driver的probe接口中，调用devm\_pwm\_get接口，获取pwm device句柄，并保存起来。

3）devm\_pwm\_get成功后，该pwm信号已经具备初始的周期和极性。后续根据需要，可以调用pwm\_config和pwm\_set\_polarity更改该pwm信号的周期、占空比和极性。

4）driver可以根据需要，调用pwm\_enable/pwm\_disable接口，打开或者关闭pwm信号的输出。

3.2 provider编写PWM driver的步骤

基于2.2章节描述的API，可以得到pwm provider（即具体的PWM驱动）使用pwm framework的方法和步骤如下：

1）创建代表该pwm driver的DTS节点，并提供platform device有关的资源信息，例如：

> /\* arch\arm\boot\dts\imx23.dtsi \*/
>   
> pwm: pwm@80064000 {
>   
>  compatible = "fsl,imx23-pwm";
>   
>  reg = <0x80064000 0x2000>;
>   
>  clocks = <&clks 30>;
>   
> #pwm-cells = <2>;
>   
>  fsl,pwm-number = <5>;
>   
>  status = "disabled";
>   
> };
>
> /\* arch\arm\boot\dts\imx23-evk.dts \*/
>   
> pwm: pwm@80064000 {
>   
>  pinctrl-names = "default";
>   
>  pinctrl-0 = <&pwm2\_pins\_a>;
>   
>  status = "okay";
>   
> };

2）定义一个pwm chip变量

3）注册相应的platform driver，并在driver的.probe()接口中，初始化pwm chip变量，至少要包括如下字段：

> dev，使用platform device中的dev指针即可；npwm；ops，至少包括config、enable、disable三个回调函数。
>
> 如果该pwm chip支持额外的flag（如PWM极性，或者自定义的flag），将PWM cell指定为3（of\_pwm\_n\_cells），of\_xlate指定为of\_pwm\_xlate\_with\_flags。

初始化完成调用pwmchip\_add接口，将chip添加到kernel中。

4）每当consumer有API调用时，kernel会以pwm device为参数，调用pwm driver提供的pwm ops，相应的回调函数可以从pwm device中取出pwm number（该number的意义driver自行解释），并操作对应的寄存器即可。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/pwm_overview.html)。
