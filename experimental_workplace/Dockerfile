To generate a high-quality Dockerfile for installing a package, we'll need to know the specific package and the Linux distribution you're targeting. For this example, let's assume you want to install `nginx` on an Ubuntu base image.

```Dockerfile
FROM ubuntu:latest

WORKDIR /app

RUN apt update && \
    apt install -y nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

However, if you're looking for a more generic Dockerfile that can install any package, you would typically do something like this:

```Dockerfile
FROM ubuntu:latest

WORKDIR /app

ARG PACKAGE_NAME

RUN apt update && \
    apt install -y ${PACKAGE_NAME}

EXPOSE 80

CMD ["command", "to", "run", "your", "package"]
```

To use this Dockerfile, you would build your Docker image with a command like this, specifying the package you want to install:

```bash
docker build -t myimage --build-arg PACKAGE_NAME=nginx .
```

And then you can run your Docker container:

```bash
docker run -p 8080:80 myimage
```

Remember, the `CMD` and `EXPOSE` instructions in the Dockerfile are examples and should be adjusted according to the specific requirements of the package you're installing.