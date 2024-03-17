# IGDB Redis-Powered Game and Book Recommendations Demo

This repository showcases a powerful demo using Redis for game and book recommendations, leveraging Redis Vector Search capabilities.

![Demo Screenshot](images/arch_pic_gabs.avif)

## Requirements

- Docker
- Docker Compose
- An internet connection for pulling Docker images and dependencies

## Setup

Before running the application, ensure Docker and Docker Compose are installed on your system. Refer to the [official Docker documentation](https://docs.docker.com/get-docker/) for installation instructions.

## Preparing for the Demo

First, clone this repository and navigate to the project directory:

```bash
git clone https://github.com/gacerioni/redis-gabs-igdb-demo.git
cd redis-gabs-igdb-demo
```

## Running the Demo

To start the demo, use the following command:

```bash
docker-compose -f docker-compose-igdb-books-demo.yml up -d
```

This command starts all the necessary services in detached mode, including the Flask application, Redis Stack, and PostgreSQL database.

To stop the demo and remove the containers, use:

```bash
docker-compose -f docker-compose-igdb-books-demo.yml down
```

## Access the App - Flask UI

After you confirmed that the workload stack is running, go to: http://localhost:5000

## Building the Docker Images

If you prefer to build the Docker images on your own, you can use the following commands:

For the Flask application:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t gacerioni/gabs-igdb-books-redis-vector-demo:1.0.0 . --push -f ./docker/Dockerfile_flask_app
```

These commands build the images for both `amd64` and `arm64` platforms and push them to the Docker Hub repository.

## Architecture

This demo includes the following components:

- **Flask Application**: A Python web application that provides a simple interface for searching games.
- **Redis Stack**: Utilized for caching search results to improve performance.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs, feature requests, or improvements.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
