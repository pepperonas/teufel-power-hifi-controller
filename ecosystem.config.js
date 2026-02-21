module.exports = {
  apps: [
    {
      name: 'teufel-power-hifi-controller',
      script: 'server.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      restart_delay: 1000,
      max_restarts: 10,
      min_uptime: '10s',
      env: {
        NODE_ENV: 'production',
        PORT: 5002
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 5002
      },
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      out_file: './logs/out.log',
      error_file: './logs/error.log',
      combine_logs: true,
      merge_logs: true,
      time: true,
      // Startup configuration
      startup_script: {
        description: 'Teufel Power HiFi Controller - Auto-start nach Boot',
        user: 'pi',
        cwd: '/home/pi/apps/powerhifi-controller'
      }
    }
  ]
};