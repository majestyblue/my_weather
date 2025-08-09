[![smithery badge](https://smithery.ai/badge/@majestyblue/my_weather)](https://smithery.ai/server/@majestyblue/my_weather)

## my_weather

### Installing via Smithery

To install my_weather for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@majestyblue/my_weather):

```bash
npx -y @smithery/cli install @majestyblue/my_weather --client claude
```

### Description

my_weather is a Model Context Protocol (MCP) server that provides weather information through an API. It integrates with applications to provide dynamic weather data.

### Features
- Current Weather: Get up-to-date weather information for any location.
- Weather Forecast: Access a 7-day weather forecast for planning purposes.

### Usage
To use my_weather, you can call its API to get weather data or set up as a local server to receive real-time updates.

### API Endpoints
- `/current`: Returns current weather details for a specified location.
- `/forecast`: Provides a weather forecast for the next seven days.

### Requirements
Before using my_weather, ensure you have Python 3.7 or later installed.

### Configuration
To configure the server, modify the `config.json` file with your preferences, including API keys and default locations.

### Development
To contribute to my_weather, clone the repository and submit pull requests for new features or bug fixes.
