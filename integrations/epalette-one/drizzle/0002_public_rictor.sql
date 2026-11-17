CREATE TABLE `invitations` (
	`id` text PRIMARY KEY NOT NULL,
	`workspace` text NOT NULL,
	`token_hash` text NOT NULL,
	`role` text NOT NULL,
	`expires_at` text NOT NULL,
	`created_by` text NOT NULL,
	`accepted_by` text,
	`revoked` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE `memberships` (
	`workspace` text NOT NULL,
	`subject` text NOT NULL,
	`display_name` text NOT NULL,
	`role` text NOT NULL,
	`active` integer DEFAULT 1 NOT NULL,
	PRIMARY KEY(`workspace`, `subject`)
);
--> statement-breakpoint
CREATE INDEX `memberships_subject` ON `memberships` (`subject`);--> statement-breakpoint
CREATE TABLE `organizations` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`created_by` text NOT NULL,
	`created_at` text NOT NULL
);
