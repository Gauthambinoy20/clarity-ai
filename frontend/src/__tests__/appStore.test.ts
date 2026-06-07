/**
 * Tests for the Zustand appStore.
 *
 * We test state mutations in isolation — no React rendering required.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '../stores/appStore';

// Reset store state between tests so they don't bleed into each other
beforeEach(() => {
  useAppStore.setState({
    themeMode: 'dark',
    detectionResult: null,
    plagiarismResult: null,
    humanizationResult: null,
    isAnalyzing: false,
    history: [],
    drawerOpen: false,
    notifications: [],
  });
});

// ---------------------------------------------------------------------------
// Theme toggle
// ---------------------------------------------------------------------------

describe('themeMode', () => {
  it('starts as dark', () => {
    expect(useAppStore.getState().themeMode).toBe('dark');
  });

  it('toggles from dark to light', () => {
    useAppStore.getState().toggleTheme();
    expect(useAppStore.getState().themeMode).toBe('light');
  });

  it('toggles back from light to dark', () => {
    useAppStore.getState().toggleTheme();
    useAppStore.getState().toggleTheme();
    expect(useAppStore.getState().themeMode).toBe('dark');
  });
});

// ---------------------------------------------------------------------------
// isAnalyzing flag
// ---------------------------------------------------------------------------

describe('isAnalyzing', () => {
  it('defaults to false', () => {
    expect(useAppStore.getState().isAnalyzing).toBe(false);
  });

  it('can be set to true', () => {
    useAppStore.getState().setIsAnalyzing(true);
    expect(useAppStore.getState().isAnalyzing).toBe(true);
  });

  it('can be reset to false', () => {
    useAppStore.getState().setIsAnalyzing(true);
    useAppStore.getState().setIsAnalyzing(false);
    expect(useAppStore.getState().isAnalyzing).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

describe('notifications', () => {
  it('starts empty', () => {
    expect(useAppStore.getState().notifications).toHaveLength(0);
  });

  it('adds a notification with the given message', () => {
    useAppStore.getState().addNotification('Test message');
    const notifications = useAppStore.getState().notifications;
    expect(notifications).toHaveLength(1);
    expect(notifications[0].message).toBe('Test message');
  });

  it('defaults notification type to info', () => {
    useAppStore.getState().addNotification('Info note');
    const n = useAppStore.getState().notifications[0];
    expect(n.type).toBe('info');
  });

  it('accepts a custom type', () => {
    useAppStore.getState().addNotification('Error!', 'error');
    const n = useAppStore.getState().notifications[0];
    expect(n.type).toBe('error');
  });

  it('marks a notification as read', () => {
    useAppStore.getState().addNotification('Mark me');
    const id = useAppStore.getState().notifications[0].id;
    useAppStore.getState().markNotificationRead(id);
    expect(useAppStore.getState().notifications[0].read).toBe(true);
  });

  it('removes a notification by id', () => {
    useAppStore.getState().addNotification('Remove me');
    const id = useAppStore.getState().notifications[0].id;
    useAppStore.getState().removeNotification(id);
    expect(useAppStore.getState().notifications).toHaveLength(0);
  });

  it('clears all notifications', () => {
    useAppStore.getState().addNotification('One');
    useAppStore.getState().addNotification('Two');
    useAppStore.getState().clearNotifications();
    expect(useAppStore.getState().notifications).toHaveLength(0);
  });

  it('new notifications are prepended (most recent first)', () => {
    useAppStore.getState().addNotification('First');
    useAppStore.getState().addNotification('Second');
    const notifications = useAppStore.getState().notifications;
    expect(notifications[0].message).toBe('Second');
    expect(notifications[1].message).toBe('First');
  });
});

// ---------------------------------------------------------------------------
// drawerOpen
// ---------------------------------------------------------------------------

describe('drawerOpen', () => {
  it('defaults to false', () => {
    expect(useAppStore.getState().drawerOpen).toBe(false);
  });

  it('can be opened', () => {
    useAppStore.getState().setDrawerOpen(true);
    expect(useAppStore.getState().drawerOpen).toBe(true);
  });

  it('can be closed again', () => {
    useAppStore.getState().setDrawerOpen(true);
    useAppStore.getState().setDrawerOpen(false);
    expect(useAppStore.getState().drawerOpen).toBe(false);
  });
});
