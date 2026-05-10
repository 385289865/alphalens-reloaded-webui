import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/sessions',
  },
  {
    path: '/sessions',
    name: 'session-list',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'SessionList',
        component: () => import('@/pages/SessionListPage.vue'),
      },
    ],
  },
  {
    path: '/sessions/:sid',
    name: 'session-detail',
    redirect: (to) => ({ path: `/sessions/${to.params.sid}/upload` }),
    component: () => import('@/layouts/SessionLayout.vue'),
    children: [
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/pages/session/UploadPage.vue'),
      },
      {
        path: 'data',
        name: 'BrowseData',
        component: () => import('@/pages/session/BrowseDataPage.vue'),
      },
      {
        path: 'configure',
        name: 'Configure',
        component: () => import('@/pages/session/AnalysisConfigPage.vue'),
        meta: { requiresUpload: true },
      },
    ],
  },
  {
    path: '/sessions/:sid/analysis/:aid',
    name: 'analysis-detail',
    redirect: (to) => `/sessions/${to.params.sid}/analysis/${to.params.aid}/progress`,
    component: () => import('@/layouts/AnalysisLayout.vue'),
    children: [
      {
        path: 'progress',
        name: 'AnalysisProgress',
        component: () => import('@/pages/session/AnalysisProgressPage.vue'),
      },
      {
        path: 'results',
        name: 'AnalysisResults',
        component: () => import('@/pages/session/AnalysisResultsPage.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/NotFoundPage.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
