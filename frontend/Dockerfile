FROM node:20-alpine
WORKDIR /app
COPY package.json tsconfig.json tsconfig.node.json vite.config.ts ./
RUN npm install
COPY . ./
EXPOSE 4173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
