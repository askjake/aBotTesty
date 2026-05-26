# Dish Chat Frontend

### System requirements
- Node.js version >=20
- Npm version >= 9.8.1
- Docker or Podman

### Useful links
- Next.js (Main framework) https://nextjs.org/
- Multi Zones https://nextjs.org/docs/pages/guides/multi-zones
- Monorepo https://turborepo.com/
- pnpm https://pnpm.io/
- Redux (State manager) https://redux.js.org/
- Antd (UI library) https://ant.design/
- Antd X (UI library) https://x.ant.design/
- Styled components (For building UI) https://styled-components.com/
- ZOD (For validating data) https://zod.dev/
- Atomic Design (Methodology for creating folders/files architecture) https://atomicdesign.bradfrost.com/chapter-2/

## Environment variables for the chats project
```bash
NEXT_PUBLIC_BACKEND_URL=http://0.0.0.0:8000
APP_ENV=local|development|production
NEXT_PUBLIC_BETA_REPORT_URL=http://localhost:3001
```

## Environment variables for the beta-reports project
```bash
NEXT_PUBLIC_BACKEND_URL=http://0.0.0.0:8000
APP_ENV=local|development|production
NEXT_PUBLIC_ROOT_FRONTEND_URL==http://localhost:3000
```


### Steps for running the project locally

Install npm packages:
```bash
pnpm i
```
Start project:
```bash
pnpm run dev
```

### Steps for running the project on the local machine

Start project:
```bash
docker-compose up -d
```

### CI/CD implementation to environments

Continuous Integration and Deployment process consists with the next stages:

>  - build_dev
>  - build:prod
>  - deploy:dev
>  - deploy:prod

Based on the fact that Frontend uses two microservices, each of stages has two substages: for chat and for backend services. The actual and default branch here this is `dev`, there is most actual code. In case of creating of new feature branch, it should be cloned from `dev` branch, not main

### How to use CI/CD deployment

**Deploy to Development**
```
git checkout dev
git checkout -b your-feature-branch
git add .
git commit -m "Your changes"
git push
```

Pipeline runs automatically because of special conditions in build substages: `build_dev → deploy:dev`
This could be reconfigured for cases when deployment will be started under `dev` branch(under discussion)

**Deploy to Production**
```
git checkout dev
git checkout -b your-feature-branch
git add .
git commit -m "Your changes"
git push
```

To start deploy to Production, the changes have to be merged into default branch(`dev` at the moment), and created a special tag with a version pattern
At the moment when `version tag` will be added, an appropriate image will be send into ECR. After this the new version tag should be updated in Chat-bot deployment repository
Then manually approve deployment in GitLab UI: `build_prod → deploy:prod → Add version tag → Change tag in Chat-bot deployment repository`

**Deployment to some particular microservice**

In case if you changed some particular microservice, conditions in gitlab pipeline will check the changes in list of the files and run `build_dev → deploy:dev` substages only for specific Dockerfile and container. This possible to check via `Gitlab UI → Build → Pipelines`