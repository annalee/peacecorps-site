'use strict';

var $ = require('jquery');

var Collapsible = function($root) {
  if ($root.length < 1) {
    throw new Error('selector missing');
  }
  this.el = $root[0];
  this.$el = $root;
  this.ccCollapsible = '.js-collapsibleItem';
  this.ccClose = '.js-close';
  // create shortcut to finding things within root.
  this.$ =  function(selector) {
    return this.$el.find(selector);
  };
  this.init.apply(this, arguments);
};

Collapsible.prototype.init = function(root, $control, opts) {
  var self = this;
  this.id = this.$el.attr('id') || '';
  this.hidden = !(opts && opts.startOpen);
  this.controlHidden = true;
  this.hideControls = (opts && opts.hideControls) || false;
  this.$control = $control;
  this.$closeButton = this.$(this.ccClose);
  if (this.$control) {
    this.$control.on('click', function(ev) {
      ev.preventDefault();
      self.hidden = false;
      self.controlHidden = true;
      // TODO fix global access.
      self.hideMultiple($('body').find(self.ccCollapsible));
      self.render();
    });
  }
  if (this.$closeButton.length) {
    this.$closeButton.on('click', function(ev) {
      ev.preventDefault();
      self.hidden = true;
      self.controlHidden = false;
      // TODO fix global access.
      self.hideMultiple($('body').find(self.ccCollapsible));
      self.render();
    });
  }
};


// TODO move to more general util
Collapsible.prototype.hideMultiple = function($els) {
  $els.each(function() {
    var $el = $(this);
    $el.attr('aria-hidden', true);
  });
  // TODO fix global access.
  $('[aria-expanded=true]').attr('aria-expanded', false);
};

Collapsible.prototype.render = function() {
  this.$el.attr('aria-hidden', this.hidden);
  this.$control && this.$control.attr('aria-expanded', true);
  $('.js-collapsibleControls').attr('aria-hidden', false);
  if (this.hideControls) {
    this.$control.attr('aria-hidden', this.controlHidden);
  }
};

module.exports = Collapsible;
