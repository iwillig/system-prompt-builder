class Spb < Formula
  desc "Compose reproducible, versioned system prompts"
  homepage "https://github.com/iwillig/system-prompt-builder"
  url "https://github.com/iwillig/system-prompt-builder.git", tag: "v0.1.2"
  version "0.1.2"
  license "AGPL-3.0-or-later"

  depends_on "python@3.14"

  resource "chevron" do
    url "https://files.pythonhosted.org/packages/source/c/chevron/chevron-0.14.0.tar.gz"
    sha256 "87613aafdf6d77b6a90ff073165a61ae5086e21ad49057aa0e53681601800ebf"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.5.0.tar.gz"
    sha256 "ba0d2089de75ea0310e2dde03160e6ca10009947fb95a182f9b54021bb272e34"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/p/pyyaml/PyYAML-6.0.3.tar.gz"
    sha256 "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Compose reproducible system prompts", shell_output("#{bin}/spb --help")
  end
end
