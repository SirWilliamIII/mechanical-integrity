# Mechanical Integrity Management System - Frontend

Vue.js frontend for the safety-critical mechanical integrity management system, providing inspection data entry and API 579 calculation results visualization.

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Features

- **Equipment Management**: Create and manage pressure vessels, storage tanks, and piping systems
- **Inspection Data Entry**: Input thickness measurements with validation for API 579 compliance
- **API 579 Results**: Visualize fitness-for-service calculations and remaining life assessments
- **Real-time Validation**: Client-side validation with strict input sanitization
- **Responsive Design**: Mobile-friendly interface for field inspections

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

## Integration with Backend

The frontend connects to the FastAPI backend running on port 8000. Ensure the backend services are running:

```bash
# Start backend (from backend/ directory)
cd ../backend
uv run uvicorn app.main:app --reload
```

## Safety-Critical Components

- **InspectionForm.vue**: Validates thickness measurements to ±0.001 inch precision
- **API579Results.vue**: Displays calculation results with safety warnings
- **ThicknessReadingsTable.vue**: Manages condition monitoring location data
