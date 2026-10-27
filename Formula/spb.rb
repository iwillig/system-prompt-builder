class Spb < Formula
  desc "Compose reproducible, versioned system prompts"
  homepage "https://github.com/iwillig/system-prompt-builder"
  url "https://github.com/iwillig/system-prompt-builder.git", tag: "v0.3.0"
  version "0.3.0"
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

  resource "sloppy-xml" do
    url "https://files.pythonhosted.org/packages/30/aa/e9473a1d98bf5a5650e6de6f88f21bd3ae9ad47b4219522904d8f09431c0/sloppy_xml-0.3.1.tar.gz"
    sha256 "c7973d8831ff3d452521da4da61bf1a96b12ffc0d560e2e6796d934d84f8d566"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Compose reproducible system prompts", shell_output("#{bin}/spb --help")
  end
end
