import { useState, useCallback } from "react";

const PRODUCTS = [
  {
    id: "snail-mucin-cream",
    handle: "ultimate-snail-mucin-cream",
    gtin: "850064676372",
    price: "34.99",
    title: "Ultimate Snail Mucin Cream",
    description:
      "A rich moisturizing cream formulated with snail secretion filtrate to help improve the appearance of skin texture and hydration.",
    image: "https://disuribeauty.com/cdn/shop/files/snail-mucin-cream.jpg",
    category: "Cream",
  },
  {
    id: "triple-collagen-cream",
    handle: "triple-collagen-firming-cream",
    gtin: "850064676334",
    price: "44.99",
    title: "Triple Collagen Firming Cream",
    description:
      "A firming cream with triple collagen complex to help support skin elasticity and reduce the appearance of fine lines.",
    image: "https://disuribeauty.com/cdn/shop/files/collagen-cream.jpg",
    category: "Cream",
  },
  {
    id: "ha-cream",
    handle: "hyaluronic-acid-intense-cream",
    gtin: "850064676310",
    price: "39.99",
    title: "Hyaluronic Acid Intense Cream",
    description:
      "An intense hydrating cream with hyaluronic acid to help improve moisture retention and skin barrier function.",
    image: "https://disuribeauty.com/cdn/shop/files/ha-cream.jpg",
    category: "Cream",
  },
  {
    id: "collagen-foam",
    handle: "triple-collagen-firming-foam",
    gtin: "850064676365",
    price: "14.99",
    title: "Triple Collagen Firming Foam",
    description:
      "A gentle foaming cleanser with collagen to help cleanse while maintaining skin moisture.",
    image: "https://disuribeauty.com/cdn/shop/files/collagen-foam.jpg",
    category: "Cleanser",
  },
  {
    id: "collagen-toner",
    handle: "triple-collagen-firming-toner",
    gtin: "850064676327",
    price: "27.99",
    title: "Triple Collagen Firming Toner",
    description:
      "A hydrating toner with collagen to help prep skin and improve absorption of subsequent skincare steps.",
    image: "https://disuribeauty.com/cdn/shop/files/collagen-toner.jpg",
    category: "Toner",
  },
  {
    id: "eye-cream",
    handle: "triple-collagen-firming-eye-cream",
    gtin: "850064676341",
    price: "33.99",
    title: "Triple Collagen Firming Eye Cream",
    description:
      "A targeted eye cream with collagen to help reduce the appearance of fine lines and puffiness around the eye area.",
    image: "https://disuribeauty.com/cdn/shop/files/eye-cream.jpg",
    category: "Eye Care",
  },
  {
    id: "collagen-essence",
    handle: "triple-collagen-firming-essence",
    gtin: "850066107188",
    price: "19.99",
    title: "Triple Collagen Firming Essence",
    description:
      "A lightweight essence with collagen to help boost skin hydration and prepare skin for deeper absorption.",
    image: "https://disuribeauty.com/cdn/shop/files/collagen-essence.jpg",
    category: "Essence",
  },
];

const SYSTEM_PROMPT = `You are a Google Merchant Center feed optimization expert specializing in K-beauty and skincare products. You write product data that maximizes Google Shopping visibility and click-through rates.

Rules:
- Titles: Max 150 characters. Format: [Key Benefit] [Product Type] | [Brand] — [Differentiator]. Lead with the highest-intent search keyword. Include brand "DISURI Beauty" near the end.
- Descriptions: 500–800 characters. Lead with the primary skin benefit. Use appearance-based language only (FDA cosmetic compliance: "helps improve the appearance of", "helps reduce the appearance of", never "treats" or "cures"). Include K-beauty origin. End with a soft CTA.
- SEO keywords: 5 high-intent Google Shopping keywords for this product.
- Return ONLY valid JSON, no markdown, no preamble.

Response format:
{
  "optimized_title": "...",
  "optimized_description": "...",
  "seo_keywords": ["...", "...", "...", "...", "..."],
  "improvement_notes": "One sentence on the key optimization made."
}`;

function buildUserPrompt(product) {
  return `Optimize this DISURI Beauty skincare product for Google Merchant Center:

Product: ${product.title}
Category: ${product.category}
Price: $${product.price}
Current title: ${product.title}
Current description: ${product.description}

Brand context: DISURI Beauty is a Korean-formulated (K-beauty) DTC skincare brand with radical ingredient transparency. Products contain clinically-backed actives at published concentrations. English/Spanish bilingual brand.`;
}

async function optimizeProduct(product, apiKey) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: buildUserPrompt(product) }],
    }),
  });

  if (!response.ok) throw new Error(`API error: ${response.status}`);
  const data = await response.json();
  const text = data.content?.[0]?.text || "{}";
  return JSON.parse(text.replace(/```json|```/g, "").trim());
}

function generateXML(products, optimized) {
  const now = new Date().toISOString();
  const esc = (s) =>
    String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const items = products
    .map((p) => {
      const opt = optimized[p.id];
      const title = opt?.optimized_title || p.title;
      const desc = opt?.optimized_description || p.description;
      return `  <item>
    <g:id>${p.handle}</g:id>
    <g:title>${esc(title)}</g:title>
    <g:description>${esc(desc)}</g:description>
    <g:link>https://disuribeauty.com/products/${p.handle}</g:link>
    <g:image_link>${esc(p.image)}</g:image_link>
    <g:price>${p.price} USD</g:price>
    <g:availability>in_stock</g:availability>
    <g:brand>DISURI Beauty</g:brand>
    <g:gtin>${p.gtin}</g:gtin>
    <g:condition>new</g:condition>
    <g:identifier_exists>yes</g:identifier_exists>
    <g:google_product_category>Health &amp; Beauty &gt; Personal Care &gt; Cosmetics &gt; Skin Care</g:google_product_category>
    <g:product_type>DISURI Beauty &gt; Skincare &gt; ${esc(p.category)}</g:product_type>
    <g:shipping>
      <g:country>US</g:country>
      <g:service>Standard</g:service>
      <g:price>0.00 USD</g:price>
    </g:shipping>
  </item>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>DISURI Beauty \u2014 Optimized GMC Feed</title>
    <link>https://disuribeauty.com</link>
    <description>AI-optimized product feed \u2014 ${now}</description>
${items}
  </channel>
</rss>`;
}

function generateOptimizedJSON(products, optimized) {
  return products.map((p) => {
    const opt = optimized[p.id];
    return {
      id: p.handle,
      optimized_title: opt?.optimized_title || null,
      optimized_description: opt?.optimized_description || null,
      seo_keywords: opt?.seo_keywords || [],
    };
  });
}

const ROSE = "#c4788a";
const ROSE_LIGHT = "#f7edf0";
const ROSE_MID = "#e8b4c0";

export default function FeedOptimizer() {
  const [optimized, setOptimized] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [isOptimizingAll, setIsOptimizingAll] = useState(false);
  const [activeTab, setActiveTab] = useState({});
  const [xmlCopied, setXmlCopied] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [apiKey, setApiKey] = useState(
    typeof import.meta !== "undefined" && import.meta.env?.VITE_ANTHROPIC_API_KEY || ""
  );
  const [showApiInput, setShowApiInput] = useState(false);

  const handleOptimize = useCallback(
    async (product) => {
      if (!apiKey) {
        setShowApiInput(true);
        return;
      }
      setLoading((l) => ({ ...l, [product.id]: true }));
      setErrors((e) => ({ ...e, [product.id]: null }));
      try {
        const result = await optimizeProduct(product, apiKey);
        setOptimized((o) => ({ ...o, [product.id]: result }));
        setActiveTab((t) => ({ ...t, [product.id]: "optimized" }));
      } catch (err) {
        setErrors((e) => ({ ...e, [product.id]: err.message }));
      } finally {
        setLoading((l) => ({ ...l, [product.id]: false }));
      }
    },
    [apiKey],
  );

  const handleOptimizeAll = useCallback(async () => {
    if (!apiKey) {
      setShowApiInput(true);
      return;
    }
    setIsOptimizingAll(true);
    for (const product of PRODUCTS) {
      if (!optimized[product.id]) {
        await handleOptimize(product);
        await new Promise((r) => setTimeout(r, 400));
      }
    }
    setIsOptimizingAll(false);
  }, [handleOptimize, optimized, apiKey]);

  const handleExport = useCallback(() => {
    const xml = generateXML(PRODUCTS, optimized);
    const blob = new Blob([xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "disuri-gmc-feed-optimized.xml";
    a.click();
    URL.revokeObjectURL(url);
  }, [optimized]);

  const handleCopyXML = useCallback(() => {
    const xml = generateXML(PRODUCTS, optimized);
    navigator.clipboard.writeText(xml).then(() => {
      setXmlCopied(true);
      setTimeout(() => setXmlCopied(false), 2000);
    });
  }, [optimized]);

  const handleExportOptimizedJSON = useCallback(() => {
    const data = generateOptimizedJSON(PRODUCTS, optimized);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "optimized_copy.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [optimized]);

  const handleCopyJSON = useCallback(() => {
    const data = generateOptimizedJSON(PRODUCTS, optimized);
    navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(() => {
      setJsonCopied(true);
      setTimeout(() => setJsonCopied(false), 2000);
    });
  }, [optimized]);

  const optimizedCount = Object.keys(optimized).length;
  const totalCount = PRODUCTS.length;

  return (
    <div
      style={{
        fontFamily: "'Georgia', serif",
        background: "#faf8f6",
        minHeight: "100vh",
        color: "#1a1411",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "#1a1411",
          padding: "20px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span
              style={{
                color: ROSE_MID,
                fontSize: 13,
                fontFamily: "monospace",
                letterSpacing: 3,
                textTransform: "uppercase",
              }}
            >
              DISURI BEAUTY
            </span>
            <span style={{ color: "#444", fontSize: 13 }}>/</span>
            <span
              style={{
                color: "#888",
                fontSize: 12,
                fontFamily: "monospace",
                letterSpacing: 1,
              }}
            >
              GMC Feed Optimizer
            </span>
          </div>
          <div
            style={{
              color: "#fff",
              fontSize: 22,
              marginTop: 4,
              fontWeight: 400,
              letterSpacing: -0.5,
            }}
          >
            AI Product Feed Studio
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {showApiInput && (
            <input
              type="password"
              placeholder="Anthropic API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              style={{
                background: "#2a2520",
                border: "1px solid #444",
                borderRadius: 8,
                padding: "8px 12px",
                color: "#ddd",
                fontSize: 12,
                fontFamily: "monospace",
                width: 220,
              }}
            />
          )}
          <button
            onClick={handleOptimizeAll}
            disabled={isOptimizingAll || optimizedCount === totalCount}
            style={{
              background:
                isOptimizingAll || optimizedCount === totalCount
                  ? "#2a2520"
                  : ROSE,
              color:
                isOptimizingAll || optimizedCount === totalCount
                  ? "#666"
                  : "#fff",
              border: "none",
              borderRadius: 8,
              padding: "10px 20px",
              fontSize: 13,
              fontFamily: "monospace",
              letterSpacing: 0.5,
              cursor:
                isOptimizingAll || optimizedCount === totalCount
                  ? "not-allowed"
                  : "pointer",
              transition: "all 0.2s",
            }}
          >
            {isOptimizingAll
              ? `Optimizing\u2026 ${optimizedCount}/${totalCount}`
              : optimizedCount === totalCount
                ? `All ${totalCount} optimized`
                : `Optimize all ${totalCount - optimizedCount} remaining`}
          </button>
          {optimizedCount > 0 && (
            <>
              <button
                onClick={handleCopyXML}
                style={{
                  background: "transparent",
                  color: "#aaa",
                  border: "1px solid #333",
                  borderRadius: 8,
                  padding: "10px 16px",
                  fontSize: 12,
                  fontFamily: "monospace",
                  cursor: "pointer",
                }}
              >
                {xmlCopied ? "Copied!" : "Copy XML"}
              </button>
              <button
                onClick={handleExport}
                style={{
                  background: "transparent",
                  color: "#aaa",
                  border: "1px solid #333",
                  borderRadius: 8,
                  padding: "10px 16px",
                  fontSize: 12,
                  fontFamily: "monospace",
                  cursor: "pointer",
                }}
              >
                Export .xml
              </button>
              <button
                onClick={handleExportOptimizedJSON}
                style={{
                  background: "transparent",
                  color: ROSE_MID,
                  border: `1px solid ${ROSE}44`,
                  borderRadius: 8,
                  padding: "10px 16px",
                  fontSize: 12,
                  fontFamily: "monospace",
                  cursor: "pointer",
                }}
              >
                {jsonCopied ? "Copied!" : "Export optimized_copy.json"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {optimizedCount > 0 && (
        <div style={{ background: "#1a1411", padding: "0 32px 16px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <span
              style={{
                color: "#666",
                fontSize: 11,
                fontFamily: "monospace",
              }}
            >
              FEED COVERAGE
            </span>
            <span
              style={{
                color: ROSE_MID,
                fontSize: 11,
                fontFamily: "monospace",
              }}
            >
              {optimizedCount} / {totalCount} SKUs
            </span>
          </div>
          <div style={{ background: "#2a2520", borderRadius: 4, height: 3 }}>
            <div
              style={{
                background: ROSE,
                height: 3,
                borderRadius: 4,
                width: `${(optimizedCount / totalCount) * 100}%`,
                transition: "width 0.5s ease",
              }}
            />
          </div>
        </div>
      )}

      {/* Product grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 20,
          padding: 32,
        }}
      >
        {PRODUCTS.map((product) => {
          const opt = optimized[product.id];
          const isLoading = loading[product.id];
          const error = errors[product.id];
          const tab = activeTab[product.id] || "original";

          return (
            <div
              key={product.id}
              style={{
                background: "#fff",
                borderRadius: 14,
                border: opt
                  ? `1px solid ${ROSE_MID}`
                  : "1px solid #e8e4e0",
                overflow: "hidden",
                transition: "border-color 0.3s, box-shadow 0.3s",
                boxShadow: opt
                  ? `0 4px 24px ${ROSE}18`
                  : "0 2px 8px rgba(0,0,0,0.04)",
              }}
            >
              {/* Card header */}
              <div
                style={{
                  background: opt ? ROSE_LIGHT : "#f5f3f0",
                  padding: "14px 18px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  borderBottom: "1px solid #ede9e5",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 11,
                      fontFamily: "monospace",
                      color: ROSE,
                      letterSpacing: 1,
                      textTransform: "uppercase",
                      marginBottom: 3,
                    }}
                  >
                    {product.category} &middot; ${product.price}
                  </div>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 500,
                      color: "#1a1411",
                    }}
                  >
                    {product.title}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      fontFamily: "monospace",
                      color: "#aaa",
                      marginTop: 2,
                    }}
                  >
                    GTIN: {product.gtin}
                  </div>
                </div>
                {opt && (
                  <span
                    style={{
                      background: ROSE,
                      color: "#fff",
                      fontSize: 10,
                      fontFamily: "monospace",
                      padding: "3px 8px",
                      borderRadius: 20,
                      letterSpacing: 1,
                    }}
                  >
                    AI
                  </span>
                )}
              </div>

              {/* Tab switcher */}
              {opt && (
                <div
                  style={{
                    display: "flex",
                    borderBottom: "1px solid #ede9e5",
                    background: "#faf8f6",
                  }}
                >
                  {["original", "optimized"].map((t) => (
                    <button
                      key={t}
                      onClick={() =>
                        setActiveTab((at) => ({ ...at, [product.id]: t }))
                      }
                      style={{
                        flex: 1,
                        padding: "8px",
                        fontSize: 11,
                        fontFamily: "monospace",
                        letterSpacing: 0.5,
                        textTransform: "uppercase",
                        border: "none",
                        background: "transparent",
                        color: tab === t ? ROSE : "#aaa",
                        borderBottom:
                          tab === t
                            ? `2px solid ${ROSE}`
                            : "2px solid transparent",
                        cursor: "pointer",
                        transition: "all 0.15s",
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}

              {/* Content */}
              <div style={{ padding: "16px 18px" }}>
                {tab === "optimized" && opt ? (
                  <>
                    <div style={{ marginBottom: 14 }}>
                      <div
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          color: ROSE,
                          letterSpacing: 1,
                          textTransform: "uppercase",
                          marginBottom: 5,
                        }}
                      >
                        Optimized title
                        <span style={{ color: "#bbb", marginLeft: 6 }}>
                          {opt.optimized_title?.length}/150
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          lineHeight: 1.5,
                          color: "#1a1411",
                          fontStyle: "italic",
                        }}
                      >
                        &ldquo;{opt.optimized_title}&rdquo;
                      </div>
                    </div>
                    <div style={{ marginBottom: 14 }}>
                      <div
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          color: ROSE,
                          letterSpacing: 1,
                          textTransform: "uppercase",
                          marginBottom: 5,
                        }}
                      >
                        Optimized description
                        <span style={{ color: "#bbb", marginLeft: 6 }}>
                          {opt.optimized_description?.length} chars
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          lineHeight: 1.65,
                          color: "#444",
                        }}
                      >
                        {opt.optimized_description}
                      </div>
                    </div>
                    {opt.seo_keywords?.length > 0 && (
                      <div style={{ marginBottom: 10 }}>
                        <div
                          style={{
                            fontSize: 10,
                            fontFamily: "monospace",
                            color: ROSE,
                            letterSpacing: 1,
                            textTransform: "uppercase",
                            marginBottom: 6,
                          }}
                        >
                          Target keywords
                        </div>
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 5,
                          }}
                        >
                          {opt.seo_keywords.map((kw, i) => (
                            <span
                              key={i}
                              style={{
                                background: ROSE_LIGHT,
                                color: "#8a4a5a",
                                fontSize: 11,
                                fontFamily: "monospace",
                                padding: "3px 8px",
                                borderRadius: 20,
                              }}
                            >
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {opt.improvement_notes && (
                      <div
                        style={{
                          background: "#f5f3f0",
                          borderRadius: 8,
                          padding: "10px 12px",
                          fontSize: 11,
                          color: "#777",
                          lineHeight: 1.5,
                          fontStyle: "italic",
                        }}
                      >
                        {opt.improvement_notes}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div style={{ marginBottom: 12 }}>
                      <div
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          color: "#aaa",
                          letterSpacing: 1,
                          textTransform: "uppercase",
                          marginBottom: 5,
                        }}
                      >
                        Current title
                        <span style={{ marginLeft: 6 }}>
                          {product.title.length}/150
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          lineHeight: 1.5,
                          color: "#444",
                          fontStyle: "italic",
                        }}
                      >
                        &ldquo;{product.title}&rdquo;
                      </div>
                    </div>
                    <div style={{ marginBottom: 16 }}>
                      <div
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          color: "#aaa",
                          letterSpacing: 1,
                          textTransform: "uppercase",
                          marginBottom: 5,
                        }}
                      >
                        Current description
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          lineHeight: 1.65,
                          color: "#666",
                        }}
                      >
                        {product.description}
                      </div>
                    </div>
                  </>
                )}

                {error && (
                  <div
                    style={{
                      background: "#fff5f5",
                      border: "1px solid #fcc",
                      borderRadius: 8,
                      padding: "8px 12px",
                      fontSize: 11,
                      color: "#c44",
                      fontFamily: "monospace",
                      marginBottom: 10,
                    }}
                  >
                    Error: {error}
                  </div>
                )}

                {!opt && (
                  <button
                    onClick={() => handleOptimize(product)}
                    disabled={isLoading}
                    style={{
                      width: "100%",
                      background: isLoading ? "#f0ede9" : "#1a1411",
                      color: isLoading ? "#aaa" : "#fff",
                      border: "none",
                      borderRadius: 8,
                      padding: "11px",
                      fontSize: 12,
                      fontFamily: "monospace",
                      letterSpacing: 1,
                      cursor: isLoading ? "not-allowed" : "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    {isLoading ? (
                      <span
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            width: 12,
                            height: 12,
                            border: `2px solid ${ROSE}`,
                            borderTopColor: "transparent",
                            borderRadius: "50%",
                            display: "inline-block",
                            animation: "spin 0.7s linear infinite",
                          }}
                        />
                        Optimizing with Claude&hellip;
                      </span>
                    ) : (
                      "Optimize with Claude \u2192"
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          textAlign: "center",
          padding: "20px 32px 40px",
          fontSize: 11,
          color: "#bbb",
          fontFamily: "monospace",
          letterSpacing: 0.5,
        }}
      >
        DISURI Beauty &middot; AI Feed Studio &middot; Powered by Claude Sonnet
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
