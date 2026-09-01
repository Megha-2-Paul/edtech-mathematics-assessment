/* Shared mathematics rendering helpers for teacher and student interfaces. */
(function () {
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#039;'
    }[c]));
  }

  function latexSafe(value) {
    return String(value)
      .replace(/\\/g, '\\backslash ')
      .replace(/[{}]/g, m => '\\' + m);
  }

  function normalizeNaturalMath(value) {
    return String(value)
      .replace(/\^\s*(\d+)/g, '^{$1}')
      .replace(/°/g, '^\\circ');
  }

  function isMathLike(value) {
    return /[0-9A-Za-zα-ωΑ-Ωπθ√∑∫≤≥≠±°^_]/.test(value) && !/^\s*$/.test(value);
  }

  function autoMath(text) {
    let out = escapeHtml(text);
    const protectedMath = [];

    // Preserve explicitly entered MathJax exactly as supplied.
    out = out.replace(/\\\((.*?)\\\)/gs, (_, expr) => {
      const token = `@@MATH${protectedMath.length}@@`;
      protectedMath.push(`\\(${expr}\\)`);
      return token;
    });

    // Fractions with a parenthesized denominator, e.g.
    // tan 45° / (1 + tan^2 45°) or (a+b)/(c+d).
    const parenthesizedFraction = /((?:[A-Za-z]+(?:\s*\^\s*\d+)?(?:\s+\d+(?:\.\d+)?°?)?|\d+(?:\.\d+)?|\([^()]+\)|[A-Za-z]+\s+\d+(?:\.\d+)?°?))\s*\/\s*\(([^()]+)\)/g;
    out = out.replace(parenthesizedFraction, (_, numerator, denominator) => {
      if (!isMathLike(numerator) || !isMathLike(denominator)) return _;
      const n = normalizeNaturalMath(latexSafe(numerator.trim()));
      const d = normalizeNaturalMath(latexSafe(denominator.trim()));
      return `\\(\\frac{${n}}{${d}}\\)`;
    });

    // Compact fractions such as 3/4, x/y and a+b/c+d are intentionally
    // limited to simple tokens so ordinary prose containing '/' is untouched.
    out = out.replace(/(?<![\w])([A-Za-zα-ωΑ-Ωπθ]+|\d+(?:\.\d+)?|\([^()]+\))\s*\/\s*([A-Za-zα-ωΑ-Ωπθ]+|\d+(?:\.\d+)?|\([^()]+\))(?![\w])/g,
      (match, numerator, denominator) => {
        if (!isMathLike(numerator) || !isMathLike(denominator)) return match;
        return `\\(\\frac{${normalizeNaturalMath(latexSafe(numerator))}}{${normalizeNaturalMath(latexSafe(denominator))}}\\)`;
      });

    // Natural powers must be wrapped in MathJax delimiters. The previous
    // implementation produced x^{2} outside MathJax, which displayed literally.
    out = out.replace(/(?<![\\w@])([A-Za-zα-ωΑ-Ωπθ√][A-Za-z0-9α-ωΑ-Ωπθ√]*?)\s*\^\s*(\d+)(?![\w}])/g,
      (_, base, exponent) => `\\(${latexSafe(base)}^{${exponent}}\\)`);

    // Degree values such as 45° should render with a true degree symbol.
    out = out.replace(/(?<![\\w@])(\d+(?:\.\d+)?)°/g,
      (_, number) => `\\(${number}^\\circ\\)`);

    // Common standalone roots typed naturally.
    out = out.replace(/√\s*\(?([^\n]+?)\)?(?=\s|$|[,.;:!?])/g,
      (_, value) => `\\(\\sqrt{${latexSafe(value.trim())}}\\)`);

    // Restore explicitly entered MathJax after natural notation conversion.
    protectedMath.forEach((math, i) => {
      out = out.replace(`@@MATH${i}@@`, math);
    });
    return out;
  }

  window.AssessmentMath = {
    escapeHtml,
    renderText(text) {
      return autoMath(text).replace(/\n/g, '<br>');
    },
    typeset(container) {
      if (window.MathJax?.typesetPromise) {
        window.MathJax.typesetClear?.([container]);
        window.MathJax.typesetPromise([container]).catch(() => {});
      }
    }
  };
})();
