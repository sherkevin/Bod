# Task: PWA Support and Offline Functionality

## Overview

Implement Progressive Web App features including Service Worker, offline support, background sync, and add-to-home-screen functionality.

## Dependencies

- Requires `frontend-framework` to be completed

## Deliverables

### 1. Service Worker Configuration

#### `public/sw.js`
```javascript
/// <reference lib="webworker" />

const CACHE_NAME = 'bod-v1';
const STATIC_CACHE = 'bod-static-v1';

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/badge-72.png',
  '/offline.html',
];

const API_CACHE = 'bod-api-v1';
const API_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first for API, cache first for static
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets
  event.respondWith(handleStaticRequest(request));
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  const cache = await caches.open(API_CACHE);

  // Try network first
  try {
    const response = await fetch(request);

    // Cache successful GET requests
    if (response.ok && request.method === 'GET') {
      const clonedResponse = response.clone();
      await cache.put(request, clonedResponse);
    }

    return response;
  } catch (error) {
    // Network failed, try cache
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }

    // Return offline fallback for specific endpoints
    if (request.url.includes('/workout/')) {
      return new Response(JSON.stringify({ offline: true, cached: true }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    throw error;
  }
}

// Handle static requests with cache-first strategy
async function handleStaticRequest(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);

  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    throw error;
  }
}

// Background sync for workout logs
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'sync-workout-logs') {
    event.waitUntil(syncWorkoutLogs());
  }

  if (event.tag === 'sync-checkins') {
    event.waitUntil(syncCheckIns());
  }
});

// Sync pending workout logs
async function syncWorkoutLogs() {
  try {
    const pendingLogs = await getPendingLogs();

    for (const log of pendingLogs) {
      try {
        const response = await fetch('/api/v1/workout/logs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(log.data),
        });

        if (response.ok) {
          await removePendingLog(log.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync log:', log.id);
      }
    }
  } catch (error) {
    console.error('[SW] Sync failed:', error);
  }
}

// Sync pending check-ins
async function syncCheckIns() {
  try {
    const pendingCheckins = await getPendingCheckins();

    for (const checkin of pendingCheckins) {
      try {
        const response = await fetch('/api/v1/checkin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(checkin.data),
        });

        if (response.ok) {
          await removePendingCheckin(checkin.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync checkin:', checkin.id);
      }
    }
  } catch (error) {
    console.error('[SW] Checkin sync failed:', error);
  }
}

// IndexedDB helpers for offline storage
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('BodOfflineDB', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('pendingLogs')) {
        db.createObjectStore('pendingLogs', { keyPath: 'id' });
      }

      if (!db.objectStoreNames.contains('pendingCheckins')) {
        db.createObjectStore('pendingCheckins', { keyPath: 'id' });
      }

      if (!db.objectStoreNames.contains('cachedPlans')) {
        db.createObjectStore('cachedPlans', { keyPath: 'planId' });
      }
    };
  });
}

async function getPendingLogs() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingLogs', 'readonly');
    const store = tx.objectStore('pendingLogs');
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removePendingLog(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingLogs', 'readwrite');
    const store = tx.objectStore('pendingLogs');
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getPendingCheckins() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingCheckins', 'readonly');
    const store = tx.objectStore('pendingCheckins');
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removePendingCheckin(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendingCheckins', 'readwrite');
    const store = tx.objectStore('pendingCheckins');
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// Push notification handling
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    vibrate: [200, 100, 200],
    data: data.data || {},
    actions: data.actions || [],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;

  if (action === 'start') {
    event.waitUntil(
      self.clients.openWindow(`/workout/${event.notification.data.session_id}`)
    );
  } else if (action === 'reply') {
    event.waitUntil(self.clients.openWindow('/messages'));
  } else {
    event.waitUntil(self.clients.openWindow('/'));
  }
});
```

### 2. PWA Manifest

#### `public/manifest.json`
```json
{
  "name": "Bod - Personal Fitness Coach",
  "short_name": "Bod",
  "description": "AI-powered personal fitness coach",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#3b82f6",
  "orientation": "portrait",
  "scope": "/",
  "icons": [
    {
      "src": "/icon-72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icon-384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshot-wide.png",
      "sizes": "1280x720",
      "type": "image/png",
      "form_factor": "wide"
    },
    {
      "src": "/screenshot-narrow.png",
      "sizes": "750x1334",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ],
  "categories": ["fitness", "health", "sports"],
  "shortcuts": [
    {
      "name": "Start Workout",
      "short_name": "Workout",
      "description": "Start today's workout",
      "url": "/workout",
      "icons": [{ "src": "/icon-96.png", "sizes": "96x96" }]
    },
    {
      "name": "View Plan",
      "short_name": "Plan",
      "description": "View workout plan",
      "url": "/plan",
      "icons": [{ "src": "/icon-96.png", "sizes": "96x96" }]
    },
    {
      "name": "My Progress",
      "short_name": "Progress",
      "description": "View progress",
      "url": "/progress",
      "icons": [{ "src": "/icon-96.png", "sizes": "96x96" }]
    }
  ]
}
```

### 3. Offline Storage Manager

#### `lib/offline-storage.ts`
```typescript
/**
 * Offline storage manager using IndexedDB
 */

interface PendingLog {
  id: string;
  sessionId: string;
  exerciseId: string;
  data: {
    set_number: number;
    weight: number;
    reps: number;
    rpe: number;
  };
  timestamp: number;
}

interface CachedPlan {
  planId: string;
  data: any;
  cachedAt: number;
}

class OfflineStorage {
  private db: IDBDatabase | null = null;
  private readonly DB_NAME = 'BodOfflineDB';
  private readonly DB_VERSION = 1;

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        if (!db.objectStoreNames.contains('pendingLogs')) {
          db.createObjectStore('pendingLogs', { keyPath: 'id' });
        }

        if (!db.objectStoreNames.contains('pendingCheckins')) {
          db.createObjectStore('pendingCheckins', { keyPath: 'id' });
        }

        if (!db.objectStoreNames.contains('cachedPlans')) {
          db.createObjectStore('cachedPlans', { keyPath: 'planId' });
        }
      };
    });
  }

  async savePendingLog(log: PendingLog): Promise<void> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('pendingLogs', 'readwrite');
    const store = tx.objectStore('pendingLogs');
    store.put(log);
  }

  async getPendingLogs(): Promise<PendingLog[]> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('pendingLogs', 'readonly');
    const store = tx.objectStore('pendingLogs');
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async removePendingLog(id: string): Promise<void> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('pendingLogs', 'readwrite');
    const store = tx.objectStore('pendingLogs');
    store.delete(id);
  }

  async cachePlan(planId: string, data: any): Promise<void> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('cachedPlans', 'readwrite');
    const store = tx.objectStore('cachedPlans');
    store.put({
      planId,
      data,
      cachedAt: Date.now(),
    } as CachedPlan);
  }

  async getCachedPlan(planId: string): Promise<CachedPlan | null> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('cachedPlans', 'readonly');
    const store = tx.objectStore('cachedPlans');
    return new Promise((resolve, reject) => {
      const request = store.get(planId);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  async clearCache(): Promise<void> {
    if (!this.db) await this.init();
    const tx = this.db!.transaction('cachedPlans', 'readwrite');
    const store = tx.objectStore('cachedPlans');
    store.clear();
  }
}

export const offlineStorage = new OfflineStorage();
```

### 4. Offline Detection Hook

#### `hooks/use-online-status.ts`
```typescript
'use client';

import { useEffect, useState } from 'react';

export function useOnlineStatus(): { online: boolean; since: number | null } {
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [since, setSince] = useState<number | null>(null);

  useEffect(() => {
    const handleOnline = () => {
      setOnline(true);
      setSince(Date.now());
    };

    const handleOffline = () => {
      setOnline(false);
      setSince(Date.now());
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { online, since };
}
```

### 5. Offline-Aware API Client

#### `lib/api-client.ts`
```typescript
import { offlineStorage } from './offline-storage';
import { toast } from '@/components/ui/use-toast';

class ApiClient {
  private baseURL = process.env.NEXT_PUBLIC_API_URL || '/api';

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      // Handle offline mode for specific endpoints
      if (endpoint.includes('/workout/logs')) {
        await this.saveOfflineRequest(endpoint, options);
        throw new Error('OFFLINE_SAVED');
      }
      throw error;
    }
  }

  async requestWithCache<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T | null> {
    // Try cache first for GET requests
    if (options.method === 'GET' || !options.method) {
      const cached = await this.getCached<T>(endpoint);
      if (cached) {
        return cached;
      }
    }

    // Then try network
    try {
      const result = await this.request<T>(endpoint, options);
      if (options.method === 'GET' || !options.method) {
        await this.setCache(endpoint, result);
      }
      return result;
    } catch (error) {
      // Return cached if network fails
      if (options.method === 'GET' || !options.method) {
        return await this.getCached<T>(endpoint);
      }
      throw error;
    }
  }

  private async saveOfflineRequest(
    endpoint: string,
    options: RequestInit
  ): Promise<void> {
    const body = options.body ? JSON.parse(options.body as string) : {};

    await offlineStorage.savePendingLog({
      id: `${Date.now()}-${Math.random()}`,
      sessionId: body.session_id || 'unknown',
      exerciseId: body.exercise_id || 'unknown',
      data: body,
      timestamp: Date.now(),
    });

    toast({
      title: 'Offline',
      description: 'Your data will be synced when you\'re back online.',
    });
  }

  private async getCached<T>(key: string): Promise<T | null> {
    // Implementation for cache retrieval
    return null;
  }

  private async setCache<T>(key: string, value: T): Promise<void> {
    // Implementation for cache storage
  }
}

export const apiClient = new ApiClient();
```

### 6. Install Prompt Component

#### `components/PWAInstallPrompt.tsx`
```typescript
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, X } from 'lucide-react';

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handler);

    // Check if already dismissed
    const dismissedStr = localStorage.getItem('pwa-prompt-dismissed');
    if (dismissedStr) {
      const dismissedTime = parseInt(dismissedStr);
      const daysSinceDismissed = (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);
      if (daysSinceDismissed < 7) {
        setShowPrompt(false);
      }
    }

    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      setShowPrompt(false);
    }

    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    setDismissed(true);
    localStorage.setItem('pwa-prompt-dismissed', Date.now().toString());
  };

  if (!showPrompt || dismissed) return null;

  return (
    <Card className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 p-4 z-50 shadow-lg">
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 p-1 hover:bg-secondary rounded"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center flex-shrink-0">
          <Download className="w-6 h-6 text-primary-foreground" />
        </div>

        <div className="flex-1">
          <h3 className="font-semibold">Install Bod App</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Add to home screen for the best experience
          </p>

          <div className="flex gap-2 mt-3">
            <Button onClick={handleInstall} size="sm">
              Install
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDismiss}>
              Not now
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
```

### 7. Offline Indicator

#### `components/OfflineIndicator.tsx`
```typescript
'use client';

import { useOnlineStatus } from '@/hooks/use-online-status';
import { Wifi, WifiOff } from 'lucide-react';
import { useEffect } from 'react';

export function OfflineIndicator() {
  const { online, since } = useOnlineStatus();

  useEffect(() => {
    if (!online) {
      // Show offline notification
      if ('serviceWorker' in navigator && 'showNotification' in ServiceWorkerRegistration.prototype) {
        // Use service worker notification
      }
    }
  }, [online]);

  if (online) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-orange-500 text-white px-4 py-2 z-50">
      <div className="container mx-auto flex items-center justify-center gap-2">
        <WifiOff className="w-4 h-4" />
        <span className="text-sm font-medium">
          You're offline. Some features may be limited.
        </span>
      </div>
    </div>
  );
}
```

### 8. Layout Integration

#### `app/layout.tsx` (partial)
```typescript
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { offlineStorage } from '@/lib/offline-storage';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize offline storage
    offlineStorage.init().catch(console.error);

    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('SW registered:', registration);
        })
        .catch((error) => {
          console.error('SW registration failed:', error);
        });
    }
  }, []);

  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#3b82f6" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body>
        <OfflineIndicator />
        {children}
        <PWAInstallPrompt />
      </body>
    </html>
  );
}
```

## Technical Requirements

- Service Worker with caching strategies
- IndexedDB for offline storage
- Background sync API
- Web App Manifest
- Install prompt handling

## Acceptance Criteria

- [ ] App can be added to home screen
- [ ] App works offline with cached data
- [ ] Workout logs saved offline sync when online
- [ ] Install prompt shows on eligible devices
- [ ] Offline indicator displays status
- [ ] Plans cached for offline viewing
- [ ] Service worker updates properly

## Notes

- Test offline functionality thoroughly
- Handle different browser behaviors
- Consider storage limits (IndexedDB quota)
- Implement cache invalidation strategy
