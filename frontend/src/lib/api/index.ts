/**
 * Central Export Hub for AI-HOS API Client & Domain Services.
 * Provides unified access while maintaining modular domain separation.
 */

export * from './client';
export * from './auth';
export * from './organizations';
export * from './patients';
export * from './doctors';
export * from './nurses';
export * from './appointments';
export * from './prescriptions';
export * from './clinical';
export * from './admin';
export * from './telehealth';
export * from './abdm';
export * from './observability';

export { default } from './client';

