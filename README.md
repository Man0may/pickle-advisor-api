# Pickleball Playability API

A Flask REST API that scores how playable outdoor pickleball conditions are, from 1 to 10, using live weather data. The service runs in Docker on AWS ECS Fargate, and GitHub Actions redeploys it automatically on every push to `main`.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey) ![Docker](https://img.shields.io/badge/Docker-container-2496ED) ![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900)

## How it works

1. A client calls `GET /score` with a latitude and longitude.
2. The API pulls current conditions from the [Open-Meteo](https://open-meteo.com/) forecast API (no API key required).
3. Four factors are scored from 1 to 10 and combined into a weighted average:

| Factor | Weight | Best range | Score drops to 1 at |
|---|---|---|---|
| Temperature | 2x | 72–76 °F | below 40 °F or about 113 °F |
| Wind speed | 2x | 8 mph or less | 25 mph |
| Chance of precipitation | 2x | 15% or less | 80% |
| Dew point (humidity) | 1x | 55 °F or less | 75 °F |

4. The response includes the score, the raw weather readings, and a recommendation message.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service info and usage examples |
| `GET` | `/score?latitude=<lat>&longitude=<lon>` | Playability score for a location |
| `GET` | `/health` | Health check used by the ECS container health check |

### Example request

```bash
curl "http://localhost:5000/score?latitude=38.89&longitude=-77.03"
```

### Example response

```json
{
  "playability_score": 9.6,
  "recommendation": "Ferb, I know what we're gonna do today! Perfect pickleball weather!",
  "weather": {
    "temperature_f": 74.1,
    "wind_mph": 6.2,
    "precipitation_probability_pct": 10,
    "dewpoint_f": 61.3
  },
  "location": { "latitude": 38.89, "longitude": -77.03 }
}
```

*(Example weather values; the score shown is what the scoring function returns for them. Real responses reflect current conditions.)*

### Errors

| Status | When |
|---|---|
| `400` | `latitude` or `longitude` is missing or not numeric |
| `502` | The Open-Meteo request fails or times out (10 s timeout) |

## Run locally

**With Python**

```bash
pip install -r requirements.txt
flask --app app.main run --port 5000
```

**With Docker**

```bash
docker build -t pickleball-advisor .
docker run -p 5000:5000 pickleball-advisor
```

The container serves the app with Gunicorn on port 5000.

## Deployment (AWS)

```
git push (main) ──► GitHub Actions ──► build Docker image ──► push to Amazon ECR
                                                                   │
                         CloudWatch Logs ◄── ECS Fargate service ◄─┘  (new task definition revision)
```

On every push to `main`, the workflow in `.github/workflows/deploy.yml` does the following:

1. Authenticates to AWS using repository secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
2. Builds the Docker image and pushes it to Amazon ECR, tagged with the commit SHA.
3. Renders `task-definition.json` with the new image.
4. Deploys it to the `pickleball-service` service on the `pickleball-cluster` ECS cluster and waits for the service to stabilize.

**Task configuration** (`task-definition.json`):
- Fargate launch type, `awsvpc` networking, 0.25 vCPU, 512 MB memory
- Container health check against `/health` every 30 seconds
- Logs shipped to CloudWatch under `/ecs/pickleball-advisor`

## Project structure

```
.
├── app/
│   └── main.py              # Flask app: routes and scoring logic
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline to ECR + ECS
├── Dockerfile               # Python 3.12-slim image served by Gunicorn
├── requirements.txt         # flask, requests, gunicorn
└── task-definition.json     # ECS Fargate task definition
```

## Tech stack

Python, Flask, Gunicorn, Docker, AWS (ECS Fargate, ECR, CloudWatch, IAM), GitHub Actions, Open-Meteo API
