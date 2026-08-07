import React from 'react';
import { createRoot } from 'react-dom/client';
import { Agentation } from 'agentation';

document.addEventListener('DOMContentLoaded', () => {
  let container = document.getElementById('agentation-root');
  if (!container) {
    container = document.createElement('div');
    container.id = 'agentation-root';
    document.body.appendChild(container);
  }
  const root = createRoot(container);
  root.render(React.createElement(Agentation));
});
