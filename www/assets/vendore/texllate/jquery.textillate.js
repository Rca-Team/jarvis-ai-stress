/*
 * textillate.js
 * http://jschr.github.com/textillate
 * MIT licensed
 */
(function ($) {
  "use strict";

  function isInEffect (effect) {
    return /In/.test(effect) || $.inArray(effect, $.fn.textillate.defaults.inEffects) >= 0;
  }

  function isOutEffect (effect) {
    return /Out/.test(effect) || $.inArray(effect, $.fn.textillate.defaults.outEffects) >= 0;
  }

  function stringToBoolean(str) {
    if (str !== "true" && str !== "false") return str;
    return (str === "true");
  }

  function getData (node) {
    var attrs = node.attributes || []
      , data = {};

    if (!attrs.length) return data;

    $.each(attrs, function (i, attr) {
      var nodeName = attr.nodeName;
      if (/^data-in-*/.test(nodeName)) {
        data.in = data.in || {};
        data.in[nodeName.replace(/data-in-/, '')] = stringToBoolean(attr.nodeValue);
      } else if (/^data-out-*/.test(nodeName)) {
        data.out = data.out || {};
        data.out[nodeName.replace(/data-out-/, '')] = stringToBoolean(attr.nodeValue);
      } else if (/^data-*/.test(nodeName)) {
        data[nodeName.replace(/data-/, '')] = stringToBoolean(attr.nodeValue);
      }
    });

    return data;
  }

  function shuffle (o) {
      for (var j, x, i = o.length; i; j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
      return o;
  }

  function animate ($t, effect, cb) {
    $t.addClass('animated ' + effect)
      .css('visibility', 'visible')
      .show();

    $t.one('animationend webkitAnimationEnd oAnimationEnd MSAnimationEnd', function () {
        $t.removeClass('animated ' + effect);
        cb && cb();
    });
  }

  function Textillate (element, options) {
    var base = this;

    base.$element = $(element);
    base.options = $.extend(true, {}, $.fn.textillate.defaults, options);

    base.init = function () {
      base.$texts = base.$element.find(base.options.selector);
      
      if (!base.$texts.length) {
        base.$texts = $('<ul class="texts"><li>' + base.$element.html() + '</li></ul>');
        base.$element.html(base.$texts);
      }

      base.$texts.hide();

      base.$current = $('<span>')
        .html(base.$texts.find(':first-child').html())
        .prependTo(base.$element);

      if (isInEffect(base.options.in.effect)) {
        base.$current.css('visibility', 'hidden');
      } else if (isOutEffect(base.options.out.effect)) {
        base.$current.css('visibility', 'visible');
      }

      base.setOptions(base.options);

      base.timeout = null;

      setTimeout(function () {
        base.options.autoStart && base.start();
      }, base.options.initialDelay)
    };

    base.setOptions = function (options) {
      base.options = options;
    };

    base.triggerEvent = function (name) {
      var e = $.Event(name + '.tlt');
      base.$element.trigger(e, base);
      return e;
    };

    base.in = function (index, cb) {
      index = index || 0;

      var $elem = base.$texts.find(':nth-child(' + ((index||0) + 1) + ')')
        , options = $.extend(true, {}, base.options, $elem.length ? getData($elem[0]) : {})
        , $tokens;

      $elem.addClass('current');

      base.triggerEvent('inAnimationBegin');

      base.$current
        .html($elem.html())
        .lettering('words');

      base.$current.find('[class^="word"]')
          .css({
            'display': 'inline-block',
            '-webkit-transform': 'translate3d(0,0,0)',
            '-moz-transform': 'translate3d(0,0,0)',
            '-o-transform': 'translate3d(0,0,0)',
            'transform': 'translate3d(0,0,0)'
          })
          .each(function () { $(this).lettering(); });

      $tokens = base.$current
        .find('[class^="char"]')
        .css('display', 'inline-block');

      if (isInEffect(options.in.effect)) {
        $tokens.css('visibility', 'hidden');
      } else if (isOutEffect(options.in.effect)) {
        $tokens.css('visibility', 'visible');
      }

      if (options.in.shuffle) {
        $tokens = shuffle($tokens);
      }

      if (options.in.sync) {
        animate($tokens, options.in.effect, function () {
          base.triggerEvent('inAnimationEnd');
          if (cb) cb();
        });
      } else {
        $tokens.each(function (i) {
          var delay = options.in.delay * i;
          setTimeout(function () {
            animate($tokens.eq(i), options.in.effect, function () {
              if (i === $tokens.length - 1) {
                base.triggerEvent('inAnimationEnd');
                if (cb) cb();
              }
            });
          }, delay);
        });
      }
    };

    base.out = function (cb) {
      var $elem = base.$texts.find(':nth-child(' + ((base.current||0) + 1) + ')')
        , $tokens = base.$current.find('[class^="char"]')
        , options = $.extend(true, {}, base.options, $elem.length ? getData($elem[0]) : {});

      base.triggerEvent('outAnimationBegin');

      if (options.out.shuffle) {
        $tokens = shuffle($tokens);
      }

      if (options.out.sync) {
        animate($tokens, options.out.effect, function () {
          base.triggerEvent('outAnimationEnd');
          if (cb) cb();
        });
      } else {
        $tokens.each(function (i) {
          var delay = options.out.delay * i;
          setTimeout(function () {
            animate($tokens.eq(i), options.out.effect, function () {
              if (i === $tokens.length - 1) {
                base.triggerEvent('outAnimationEnd');
                if (cb) cb();
              }
            });
          }, delay);
        });
      }
    };

    base.start = function (index) {
      setTimeout(function () {
        base.triggerEvent('start');

        (function run (index) {
          base.in(index, function () {
            var length = base.$texts.children().length;

            base.current = index;

            if (base.options.loop) {
              base.timeout = setTimeout(function () {
                base.out(function () {
                  run((index + 1) % length);
                });
              }, base.options.minDisplayTime);
            }
          });
        }(index || 0));
      }, base.options.initialDelay);
    };

    base.stop = function () {
      if (base.timeout) {
        clearTimeout(base.timeout);
        base.timeout = null;
      }
    };

    base.init();
  }

  $.fn.textillate = function (settings, args) {
    return this.each(function () {
      var $this = $(this)
        , data = $this.data('textillate')
        , options = $.extend(true, {}, $.fn.textillate.defaults, $.fn.textillate.defaults.in, $.fn.textillate.defaults.out, typeof settings === 'object' && settings);

      if (!data) {
        $this.data('textillate', (data = new Textillate(this, options)));
      } else if (typeof settings === 'string') {
        data[settings].apply(data, [].concat(args));
      } else {
        data.setOptions.call(data, options);
      }
    });
  };

  $.fn.textillate.defaults = {
    selector: '.texts',
    loop: false,
    minDisplayTime: 2000,
    initialDelay: 0,
    in: {
      effect: 'fadeInLeftBig',
      delayScale: 1.5,
      delay: 50,
      sync: false,
      reverse: false,
      shuffle: false,
      callback: function () {}
    },
    out: {
      effect: 'hinge',
      delayScale: 1.5,
      delay: 50,
      sync: false,
      reverse: false,
      shuffle: false,
      callback: function () {}
    },
    autoStart: true,
    inEffects: [],
    outEffects: [ 'hinge' ],
    callback: function () {},
    type: 'char'
  };

}(jQuery));
