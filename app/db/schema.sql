-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Define Enum for User Role
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('guest', 'user', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Note: If using Supabase Auth, this might be redundant or managed in auth.users
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    bio TEXT,
    role user_role DEFAULT 'user',
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Profile information
    website_url VARCHAR(500),
    twitter_handle VARCHAR(50),
    github_handle VARCHAR(50),
    linkedin_url VARCHAR(500),
    
    -- Statistics (denormalized)
    total_prompts INT DEFAULT 0,
    total_followers INT DEFAULT 0,
    total_following INT DEFAULT 0,
    total_views_received INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    icon_url VARCHAR(500),
    color_code VARCHAR(7), -- Hex color code
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Statistics
    prompt_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Categories Indices
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
CREATE INDEX IF NOT EXISTS idx_categories_display_order ON categories(display_order);
CREATE INDEX IF NOT EXISTS idx_categories_is_active ON categories(is_active);

-- Trigger for updated_at (Categories)
DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;
CREATE TRIGGER update_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Prompts Enums
DO $$ BEGIN
    CREATE TYPE prompt_type_enum AS ENUM ('text_generation', 'image_generation', 'video_generation', 'code_generation', 'audio_generation', 'other');
    CREATE TYPE privacy_status_enum AS ENUM ('public', 'private', 'unlisted');
    CREATE TYPE status_enum AS ENUM ('draft', 'published', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Prompts Table
CREATE TABLE IF NOT EXISTS prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    
    -- Basic Information
    title VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_text TEXT NOT NULL,
    
    -- Classification
    prompt_type prompt_type_enum NOT NULL,
    category_id UUID NOT NULL, -- Assumes categories table exists
    
    -- Privacy & Status
    privacy_status privacy_status_enum DEFAULT 'public',
    status status_enum DEFAULT 'draft',
    is_featured BOOLEAN DEFAULT FALSE,
    featured_at TIMESTAMP WITH TIME ZONE,
    
    -- Statistics
    view_count INT DEFAULT 0,
    bookmark_count INT DEFAULT 0,
    rating_count INT DEFAULT 0,
    rating_sum INT DEFAULT 0,
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    fork_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    
    -- Version control
    version INT DEFAULT 1,
    parent_prompt_id UUID,
    forked_from_id UUID,
    
    -- SEO & Metadata
    slug VARCHAR(300) UNIQUE,
    meta_description TEXT,
    
    -- Timestamps
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (parent_prompt_id) REFERENCES prompts(id) ON DELETE SET NULL,
    FOREIGN KEY (forked_from_id) REFERENCES prompts(id) ON DELETE SET NULL
);

-- Prompts Indices
CREATE INDEX IF NOT EXISTS idx_prompts_user_id ON prompts(user_id);
CREATE INDEX IF NOT EXISTS idx_prompts_type ON prompts(prompt_type);
CREATE INDEX IF NOT EXISTS idx_prompts_category_id ON prompts(category_id);
CREATE INDEX IF NOT EXISTS idx_prompts_privacy ON prompts(privacy_status);
CREATE INDEX IF NOT EXISTS idx_prompts_status ON prompts(status);
CREATE INDEX IF NOT EXISTS idx_prompts_featured ON prompts(is_featured);
CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_prompts_avg_rating ON prompts(average_rating);
CREATE INDEX IF NOT EXISTS idx_prompts_view_count ON prompts(view_count);
CREATE INDEX IF NOT EXISTS idx_prompts_slug ON prompts(slug);

-- Fulltext Search Index (PostgreSQL GIN)
CREATE INDEX IF NOT EXISTS idx_prompts_search ON prompts USING GIN (to_tsvector('english', title || ' ' || coalesce(description, '') || ' ' || prompt_text));

-- Trigger for updated_at (Prompts)
DROP TRIGGER IF EXISTS update_prompts_updated_at ON prompts;
CREATE TRIGGER update_prompts_updated_at
    BEFORE UPDATE ON prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Prompt Variables Enums
DO $$ BEGIN
    CREATE TYPE variable_data_type_enum AS ENUM ('text', 'number', 'select', 'multiline', 'boolean');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Prompt Variables Table
CREATE TABLE IF NOT EXISTS prompt_variables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    
    variable_name VARCHAR(100) NOT NULL,
    variable_key VARCHAR(100) NOT NULL, -- e.g., "product_name", "tone"
    description TEXT,
    default_value TEXT,
    data_type variable_data_type_enum DEFAULT 'text',
    is_required BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    
    -- For select type variables
    options JSONB NULL, -- Using JSONB for better performance in Postgres
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
);

-- Prompt Variables Indices
CREATE INDEX IF NOT EXISTS idx_prompt_variables_prompt_id ON prompt_variables(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_variables_order ON prompt_variables(prompt_id, display_order);

-- Trigger for updated_at (Prompt Variables)
DROP TRIGGER IF EXISTS update_prompt_variables_updated_at ON prompt_variables;
CREATE TRIGGER update_prompt_variables_updated_at
    BEFORE UPDATE ON prompt_variables
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Tags Table
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    
    -- Statistics
    usage_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tags Indices
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_slug ON tags(slug);
CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags(usage_count);

-- Trigger for updated_at (Tags)
DROP TRIGGER IF EXISTS update_tags_updated_at ON tags;
CREATE TRIGGER update_tags_updated_at
    BEFORE UPDATE ON tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Prompt Tags Table (Many-to-Many)
CREATE TABLE IF NOT EXISTS prompt_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    tag_id UUID NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    
    CONSTRAINT unique_prompt_tag UNIQUE (prompt_id, tag_id)
);

-- Prompt Tags Indices
CREATE INDEX IF NOT EXISTS idx_prompt_tags_prompt_id ON prompt_tags(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_tags_tag_id ON prompt_tags(tag_id);

-- Prompt Ratings Table
CREATE TABLE IF NOT EXISTS prompt_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CONSTRAINT unique_user_prompt_rating UNIQUE (user_id, prompt_id)
);

-- Prompt Ratings Indices
CREATE INDEX IF NOT EXISTS idx_prompt_ratings_prompt_id ON prompt_ratings(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_ratings_user_id ON prompt_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_ratings_rating ON prompt_ratings(rating);

-- Trigger for updated_at (Prompt Ratings)
DROP TRIGGER IF EXISTS update_prompt_ratings_updated_at ON prompt_ratings;
CREATE TRIGGER update_prompt_ratings_updated_at
    BEFORE UPDATE ON prompt_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Collections Table
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    slug VARCHAR(150),
    
    -- Privacy
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Statistics
    prompt_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Collections Indices
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collections_slug ON collections(slug);
CREATE INDEX IF NOT EXISTS idx_collections_is_public ON collections(is_public);

-- Trigger for updated_at (Collections)
DROP TRIGGER IF EXISTS update_collections_updated_at ON collections;
CREATE TRIGGER update_collections_updated_at
    BEFORE UPDATE ON collections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Bookmarks Table
CREATE TABLE IF NOT EXISTS bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    prompt_id UUID NOT NULL,
    collection_id UUID, -- Optional: Can be linked to a collections table later
    
    -- Optional notes
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL,
    
    CONSTRAINT unique_user_prompt_bookmark UNIQUE (user_id, prompt_id)
);

-- Bookmarks Indices
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_prompt_id ON bookmarks(prompt_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_collection_id ON bookmarks(collection_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at ON bookmarks(created_at);

-- Follows Table
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    follower_id UUID NOT NULL,
    following_id UUID NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CONSTRAINT unique_follow UNIQUE (follower_id, following_id),
    CONSTRAINT check_not_self_follow CHECK (follower_id != following_id)
);

-- Follows Indices
CREATE INDEX IF NOT EXISTS idx_follows_follower_id ON follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following_id ON follows(following_id);

-- Prompt Views Table
CREATE TABLE IF NOT EXISTS prompt_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    user_id UUID, -- NULL for guest users
    
    -- User context
    ip_address VARCHAR(45),
    user_agent TEXT,
    referrer VARCHAR(500),
    
    -- Geographic data (for future analytics)
    country_code CHAR(2),
    city VARCHAR(100),
    
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Prompt Views Indices
CREATE INDEX IF NOT EXISTS idx_prompt_views_prompt_id ON prompt_views(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_views_user_id ON prompt_views(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_views_viewed_at ON prompt_views(viewed_at);

-- Prompt Outputs Enums
DO $$ BEGIN
    CREATE TYPE output_type_enum AS ENUM ('text', 'image', 'video', 'audio', 'code');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Prompt Outputs Table
CREATE TABLE IF NOT EXISTS prompt_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    user_id UUID NOT NULL, -- Who created this output example
    
    title VARCHAR(255),
    output_text TEXT,
    output_url VARCHAR(500), -- For image/video outputs
    output_type output_type_enum NOT NULL,
    
    -- Variable values used for this output
    variable_values JSONB, -- JSONB for better performance
    
    -- Moderation
    is_approved BOOLEAN DEFAULT TRUE,
    
    display_order INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Prompt Outputs Indices
CREATE INDEX IF NOT EXISTS idx_prompt_outputs_prompt_id ON prompt_outputs(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_outputs_user_id ON prompt_outputs(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_outputs_display_order ON prompt_outputs(prompt_id, display_order);

-- Trigger for updated_at (Prompt Outputs)
DROP TRIGGER IF EXISTS update_prompt_outputs_updated_at ON prompt_outputs;
CREATE TRIGGER update_prompt_outputs_updated_at
    BEFORE UPDATE ON prompt_outputs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trending Prompts Table
CREATE TABLE IF NOT EXISTS trending_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    
    -- Trending score calculation
    trending_score DECIMAL(10,2) NOT NULL,
    views_last_24h INT DEFAULT 0,
    ratings_last_24h INT DEFAULT 0,
    bookmarks_last_24h INT DEFAULT 0,
    
    rank INT NOT NULL,
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    
    CONSTRAINT unique_prompt_trending UNIQUE (prompt_id)
);

-- Trending Prompts Indices
CREATE INDEX IF NOT EXISTS idx_trending_prompts_rank ON trending_prompts(rank);
CREATE INDEX IF NOT EXISTS idx_trending_prompts_score ON trending_prompts(trending_score);
CREATE INDEX IF NOT EXISTS idx_trending_prompts_expires ON trending_prompts(expires_at);

-- Notifications Enum
DO $$ BEGIN
    CREATE TYPE notification_type_enum AS ENUM ('new_follower', 'prompt_rated', 'prompt_commented', 'prompt_featured', 'mention', 'system');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    
    type notification_type_enum NOT NULL,
    
    title VARCHAR(255) NOT NULL,
    message TEXT,
    
    -- Reference to related entity
    related_entity_type VARCHAR(50), -- 'prompt', 'user', 'comment'
    related_entity_id UUID,
    
    -- Action URL
    action_url VARCHAR(500),
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notifications Indices
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);

-- Comments Table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Threading support
    parent_comment_id UUID,
    
    content TEXT NOT NULL,
    
    -- Moderation
    is_approved BOOLEAN DEFAULT TRUE,
    is_edited BOOLEAN DEFAULT FALSE,
    
    -- Engagement
    upvote_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_comment_id) REFERENCES comments(id) ON DELETE CASCADE
);

-- Comments Indices
CREATE INDEX IF NOT EXISTS idx_comments_prompt_id ON comments(prompt_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Trigger for updated_at (Comments)
DROP TRIGGER IF EXISTS update_comments_updated_at ON comments;
CREATE TRIGGER update_comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comment Votes Enum
DO $$ BEGIN
    CREATE TYPE vote_type_enum AS ENUM ('upvote', 'downvote');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Comment Votes Table
CREATE TABLE IF NOT EXISTS comment_votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id UUID NOT NULL,
    user_id UUID NOT NULL,
    vote_type vote_type_enum NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CONSTRAINT unique_user_comment_vote UNIQUE (user_id, comment_id)
);

-- Comment Votes Indices
CREATE INDEX IF NOT EXISTS idx_comment_votes_comment_id ON comment_votes(comment_id);
CREATE INDEX IF NOT EXISTS idx_comment_votes_user_id ON comment_votes(user_id);

-- Reports Enums
DO $$ BEGIN
    CREATE TYPE reportable_type_enum AS ENUM ('prompt', 'comment', 'user');
    CREATE TYPE report_reason_enum AS ENUM ('spam', 'inappropriate', 'copyright', 'misleading', 'other');
    CREATE TYPE report_status_enum AS ENUM ('pending', 'reviewing', 'resolved', 'dismissed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL,
    
    -- What's being reported
    reportable_type reportable_type_enum NOT NULL,
    reportable_id UUID NOT NULL,
    
    reason report_reason_enum NOT NULL,
    description TEXT,
    
    -- Moderation
    status report_status_enum DEFAULT 'pending',
    reviewed_by UUID,
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Reports Indices
CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON reports(reporter_id);
CREATE INDEX IF NOT EXISTS idx_reports_reportable ON reports(reportable_type, reportable_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);

-- Trigger for updated_at (Reports)
DROP TRIGGER IF EXISTS update_reports_updated_at ON reports;
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();














