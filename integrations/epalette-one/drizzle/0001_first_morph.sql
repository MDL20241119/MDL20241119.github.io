CREATE TABLE `integration_credentials` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`subject` text NOT NULL,
	`role` text NOT NULL,
	`token_hash` text NOT NULL,
	`expires_at` text NOT NULL,
	`revoked` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE INDEX `credentials_owner` ON `integration_credentials` (`owner`);