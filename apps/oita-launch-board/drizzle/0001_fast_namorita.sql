CREATE TABLE `login_attempts` (
	`bucket` text PRIMARY KEY NOT NULL,
	`attempts` integer NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_login_attempts_expires` ON `login_attempts` (`expires_at`);--> statement-breakpoint
CREATE TABLE `shared_access` (
	`id` integer PRIMARY KEY NOT NULL,
	`password_hash` text NOT NULL,
	`salt` text NOT NULL,
	`version` integer NOT NULL,
	`enabled` integer DEFAULT 0 NOT NULL,
	`role` text DEFAULT 'editor' NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `shared_sessions` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`csrf` text NOT NULL,
	`version` integer NOT NULL,
	`expires_at` integer NOT NULL,
	`idle_until` integer NOT NULL,
	`last_seen` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_shared_sessions_expires` ON `shared_sessions` (`expires_at`);