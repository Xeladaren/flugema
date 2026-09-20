export default {
  template: `<div style="display: none"></div>`,

  props: {
    watch: { type: Boolean, default: false },
    high_accuracy: { type: Boolean, default: true },
    timeout: { type: Number, default: 10000 },   // ms
    maximum_age: { type: Number, default: 0 },   // ms
  },

  emits: ['position', 'error'],

  data() {
    return { watch_id: null };
  },

  mounted() {
    if (this.watch) this.start();
  },

  beforeUnmount() {
    this.stop();
  },

  methods: {
    _options() {
      return {
        enableHighAccuracy: this.high_accuracy,
        timeout: this.timeout,
        maximumAge: this.maximum_age,
      };
    },

    _serialize(p) {
      return {
        latitude: p.coords.latitude,
        longitude: p.coords.longitude,
        accuracy: p.coords.accuracy,
        altitude: p.coords.altitude,
        altitude_accuracy: p.coords.altitudeAccuracy,
        heading: p.coords.heading,
        speed: p.coords.speed,
        timestamp: p.timestamp,
      };
    },

    _ok(p) {
      this.$emit('position', this._serialize(p));
    },

    _ko(err) {
      this.$emit('error', { code: err.code, message: err.message });
    },

    _unsupported() {
      if (navigator.geolocation) return false;
      this.$emit('error', { code: -1, message: 'Geolocation API non disponible (HTTPS requis ?)' });
      return true;
    },

    // --- méthodes appelables depuis Python via run_method() ---

    request() {
      if (this._unsupported()) return;
      navigator.geolocation.getCurrentPosition(this._ok, this._ko, this._options());
    },

    start() {
      if (this._unsupported() || this.watch_id !== null) return;
      this.watch_id = navigator.geolocation.watchPosition(this._ok, this._ko, this._options());
    },

    stop() {
      if (this.watch_id !== null) {
        navigator.geolocation.clearWatch(this.watch_id);
        this.watch_id = null;
      }
    },
  },
};