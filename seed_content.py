import sys
import os
from datetime import datetime
import uuid

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import BlogPost, User

def seed_blogs():
    db = SessionLocal()
    print("✍️  Writing Dummy Blog Posts...")

    # 1. Get an Author (We use the Admin or the first user found)
    author = db.query(User).filter(User.role == "admin").first()
    if not author:
        author = db.query(User).first()
        if not author:
            print("❌ No users found! Please run the main seed.py first.")
            return

    # 2. Define Content
    blogs_data = [
        {
            "title": "5 Signs You Are Wearing the Wrong Bra Size",
            "slug": "5-signs-wrong-bra-size",
            "content": """
                <p>Did you know that 80% of women are wearing the wrong bra size? It’s not just uncomfortable; it can lead to back pain and poor posture.</p>
                <h3>1. The Band Rides Up</h3>
                <p>If your bra band is arching up your back, it’s too big. The support comes from the band, not the straps.</p>
                <h3>2. The Quad-Boob Effect</h3>
                <p>If your cups are cutting into your breast tissue, creating a 'four boob' look, you need to go up a cup size immediately.</p>
                <h3>3. Slipping Straps</h3>
                <p>Constantly pulling up your straps? It might not be the straps' fault—it could be that your cups aren't filling out properly.</p>
                <p><strong>Solution:</strong> Book a virtual consultation with us today!</p>
            """,
            "featured_image": "/assets/blogs/fit-guide.jpg",
            "is_published": True
        },
        {
            "title": "The Art of Lingerie Care: Make Your Sets Last Forever",
            "slug": "lingerie-care-guide",
            "content": """
                <p>Your lingerie is an investment. Here is how to treat it with respect.</p>
                <ul>
                    <li><strong>Hand Wash Only:</strong> The washing machine is the enemy of underwires.</li>
                    <li><strong>Use Cold Water:</strong> Hot water breaks down the elasticity.</li>
                    <li><strong>Never Tumble Dry:</strong> Heat destroys the delicate lace fibers. Always air dry flat.</li>
                </ul>
                <p>Treat them well, and they will support you for years.</p>
            """,
            "featured_image": "/assets/blogs/washing-care.jpg",
            "is_published": True
        },
        {
            "title": "Client Diary: How a Virtual Fitting Changed My Posture",
            "slug": "client-diary-posture-change",
            "content": """
                <p><em>"I thought back pain was just part of my life. Then I met Mrs. Kiraka."</em></p>
                <p>I was wearing a 36C for ten years. During our Google Meet session, the consultant noticed instantly that my band was too loose. She switched me to a 32E.</p>
                <p>The difference was instant. My shoulders relaxed, my back straightened, and my clothes fit better. I'll never buy off the rack again!</p>
            """,
            "featured_image": "/assets/blogs/client-story.jpg",
            "is_published": True
        },
        {
            # A PENDING STORY (To test Admin Approval)
            "title": "My Summer Collection Favorites",
            "slug": "user-summer-favorites",
            "content": "<p>I just bought the new Freya set and I am in LOVE! The yellow color is perfect for summer...</p>",
            "featured_image": "/assets/blogs/summer-collection.jpg",
            "is_published": False # <--- Hidden! Needs approval.
        }
    ]

    # 3. Insert Data
    for post in blogs_data:
        # Check if exists
        existing = db.query(BlogPost).filter(BlogPost.slug == post["slug"]).first()
        if not existing:
            new_post = BlogPost(
                title=post["title"],
                slug=post["slug"],
                content=post["content"],
                featured_image=post["featured_image"],
                is_published=post["is_published"],
                author_id=author.id,
                published_at=datetime.utcnow()
            )
            db.add(new_post)
            print(f"✅ Created: {post['title']}")
        else:
            print(f"   Skipped: {post['title']} (Already exists)")

    db.commit()
    db.close()
    print("🎉 Blog Content Seeded Successfully!")

if __name__ == "__main__":
    seed_blogs()